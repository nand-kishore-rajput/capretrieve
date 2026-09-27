"""
Offline replay: re-plan every logged CapRetrieve run under modified
conditions. No LLM calls; the analyzer output stored in each log record is
fed straight back into plan().

    python -m capretrieve.evaluation.replay --batch-id main heldout

Writes reports/<batches>_replay.md (and prints it). Three experiments:

1. Manifest-field ablation. One field at a time is masked on EVERY
   manifest, so it no longer tells the planner anything:
     booleans            -> False   (e.g. no source declares that it leaks)
     everything else     -> "__masked__", a value no rule matches (with
                            `.value`/`.name`, so Enum-typed fields work too)
   Question answered: which declared capability does each scenario need?

2. Requirement-field ablation. One analyzer output field at a time is
   reset to its neutral value for every run (see REQUIREMENT_NEUTRAL).
   Question answered: which inferred requirement does each scenario need?

3. Threshold sweep over planner.selection.RELATIVE_THRESHOLD.
   Question answered: how close to the cutoff are the results?

Before any of that, an unmodified replay must reproduce the logged plans.
If it doesn't, the planner has changed since the batch was run, and the
report says so at the top.

Scoring is identical to compare.py (is_correct / violates), over scored
scenarios only (status active or held_out).
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from capretrieve.evaluation.compare import (
    Expectation,
    final_records,
    is_correct,
    load_expectations,
    violates,
)
from capretrieve.evaluation.records import RunRecord
from capretrieve.evaluation.runner import DEFAULT_OUT_DIR, DEFAULT_SCENARIOS

MASKED = "__masked__"
MANIFEST_FIELDS = ["query_leaks_externally", "privacy_tier", "freshness", "paradigm"]
REQUIREMENT_NEUTRAL: dict[str, Any] = {
    "privacy_sensitivity": "none",
    "expects_personal_knowledge": False,
    "needs_freshness": "any",
    "relational": False,
    "paradigm_hint": None,
    "seed_entity": None,
}
DEFAULT_THRESHOLDS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]


# ── replay core ──────────────────────────────────────────────────────────


class Replayer:
    def __init__(
        self,
        plan_fn: Callable[[list[Any], Any], Any],
        make_requirements: Callable[[dict], Any],
        manifests: Sequence[Any],
    ) -> None:
        self.plan_fn = plan_fn
        self.make_requirements = make_requirements
        self.manifests = list(manifests)

    def run(
        self,
        records: Sequence[RunRecord],
        manifests: Sequence[Any] | None = None,
        requirement_update: dict[str, Any] | None = None,
    ) -> list[RunRecord]:
        ms = list(manifests if manifests is not None else self.manifests)
        out = []
        for r in records:
            try:
                req = self.make_requirements(r.requirements)
                if requirement_update:
                    # model_copy skips validation on purpose: the masked
                    # value only has to be passed through, not be legal
                    req = req.model_copy(update=requirement_update)
                p = self.plan_fn(ms, req)
                out.append(r.model_copy(update={
                    "selected": list(p.selected_connector_ids),
                    "excluded": {
                        d.connector_id: d.exclusion_reason.constraint
                        for d in p.decisions if d.exclusion_reason is not None
                    },
                    "error": None,
                }))
            except Exception as exc:  # a crashing variant counts as incorrect
                out.append(r.model_copy(update={
                    "selected": [], "excluded": {}, "error": f"{type(exc).__name__}: {exc}",
                }))
        return out


class MaskedValue(str):
    """Placeholder that behaves like a str-Enum member (has `.value`) but
    equals no real enum value, so every rule that checks the field treats it
    as 'not declared'."""

    @property
    def value(self) -> str:
        return str(self)

    @property
    def name(self) -> str:
        return str(self)


def mask_manifests(manifests: Sequence[Any], field: str) -> list[Any]:
    def masked_value(m: Any) -> Any:
        return False if isinstance(getattr(m, field), bool) else MaskedValue(MASKED)

    return [m.model_copy(update={field: masked_value(m)}) for m in manifests]


@contextmanager
def patched_threshold(selection_module: ModuleType, value: float) -> Iterator[None]:
    old = selection_module.RELATIVE_THRESHOLD
    selection_module.RELATIVE_THRESHOLD = value
    try:
        yield
    finally:
        selection_module.RELATIVE_THRESHOLD = old


# ── scoring ──────────────────────────────────────────────────────────────


@dataclass
class Score:
    label: str
    per_scenario: dict[str, tuple[int, int]]  # sid -> (correct, n)
    original: tuple[int, int]
    held_out: tuple[int, int]
    violations: int
    changed: int  # runs whose plan differs from the logged plan
    errors: int
    first_error: str | None = None


def score(
    label: str,
    replayed: Sequence[RunRecord],
    logged: Sequence[RunRecord],
    exps: dict[str, Expectation],
) -> Score:
    per: dict[str, list[int]] = {}
    orig, held = [0, 0], [0, 0]
    viol = changed = errors = 0
    first_error = None
    for new, old in zip(replayed, logged):
        exp = exps.get(new.scenario_id)
        if exp is None or not exp.active:
            continue
        ok = is_correct(new, exp)
        cell = per.setdefault(new.scenario_id, [0, 0])
        cell[0] += ok
        cell[1] += 1
        bucket = held if exp.held_out else orig
        bucket[0] += ok
        bucket[1] += 1
        viol += violates(new, exp)
        changed += sorted(new.selected) != sorted(old.selected)
        errors += new.error is not None
        if new.error and first_error is None:
            first_error = new.error
    return Score(
        label, {k: (v[0], v[1]) for k, v in per.items()},
        tuple(orig), tuple(held), viol, changed, errors, first_error,
    )


# ── rendering ────────────────────────────────────────────────────────────


def _frac(c: int, n: int) -> str:
    return f"{c}/{n}" if n else "-"


def _pct(c: int, n: int) -> str:
    return f"{100 * c / n:.0f}%" if n else "-"


def render_table(scores: Sequence[Score], scenario_ids: Sequence[str]) -> str:
    header = ["Variant", *scenario_ids, "Original", "Held-out", "All", "Violations", "Plans changed"]
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    for s in scores:
        allc = s.original[0] + s.held_out[0]
        alln = s.original[1] + s.held_out[1]
        row = [s.label]
        row += [_frac(*s.per_scenario.get(sid, (0, 0))) for sid in scenario_ids]
        row += [_pct(*s.original), _pct(*s.held_out), f"**{_pct(allc, alln)}**",
                str(s.violations), str(s.changed) + (f" ({s.errors} errors)" if s.errors else "")]
        lines.append("| " + " | ".join(row) + " |")
    notes = [f"- `{s.label}`: {s.errors} run(s) failed, first error: `{s.first_error}`"
             for s in scores if s.errors]
    return "\n".join(lines + ([""] + notes if notes else []))


def run_all(
    replayer: Replayer,
    records: Sequence[RunRecord],
    exps: dict[str, Expectation],
    selection_module: ModuleType,
    thresholds: Sequence[float],
    name: str,
) -> str:
    sids = [s for s in exps if exps[s].active and any(r.scenario_id == s for r in records)]
    base_replay = replayer.run(records)
    base = score("baseline (unchanged)", base_replay, records, exps)

    out = [f"# Replay analysis: `{name}`", ""]
    out.append(f"CapRetrieve runs replayed: {len(records)} (scored scenarios only in tables). "
               "No LLM calls: each run's logged analyzer output is re-planned.")
    out.append("")
    mismatched = sum(sorted(a.selected) != sorted(b.selected) for a, b in zip(base_replay, records))
    if mismatched:
        out.append(f"**Warning: unmodified replay differs from the log in {mismatched} run(s).** "
                   "The planner or manifests changed since these batches ran; "
                   "results below describe the CURRENT planner.")
    else:
        out.append("Determinism check passed: unmodified replay reproduces every logged plan.")

    out += ["", "## 1. Manifest-field ablation", ""]
    out.append("One field masked on every manifest (booleans set to false, other fields set "
               "to a value no rule matches).")
    out.append("")
    fields = [f for f in MANIFEST_FIELDS if all(hasattr(m, f) for m in replayer.manifests)]
    scores = [base] + [
        score(f"− {f}", replayer.run(records, manifests=mask_manifests(replayer.manifests, f)), records, exps)
        for f in fields
    ]
    out.append(render_table(scores, sids))

    out += ["", "## 2. Requirement-field ablation", ""]
    out.append("One analyzer output field reset to a neutral value for every run: "
               + ", ".join(f"`{k}={v!r}`" for k, v in REQUIREMENT_NEUTRAL.items()) + ".")
    out.append("")
    present = [k for k in REQUIREMENT_NEUTRAL if records and k in (records[0].requirements or {})]
    scores = [base] + [
        score(f"− {k}", replayer.run(records, requirement_update={k: REQUIREMENT_NEUTRAL[k]}), records, exps)
        for k in present
    ]
    out.append(render_table(scores, sids))

    out += ["", "## 3. Threshold sweep", ""]
    current = selection_module.RELATIVE_THRESHOLD
    out.append(f"`RELATIVE_THRESHOLD` varied (see planner/selection.py for how it is "
               f"applied); current value is **{current}**.")
    out.append("")
    values = sorted(set(thresholds) | {current})
    scores = []
    for t in values:
        with patched_threshold(selection_module, t):
            label = f"{t:g}" + (" (current)" if t == current else "")
            scores.append(score(label, replayer.run(records), records, exps))
    if len({tuple(sorted(s.per_scenario.items())) for s in scores}) == 1 and len(values) > 1:
        out.append("**Warning: every threshold gave identical results.** Check that "
                   "select() reads RELATIVE_THRESHOLD at call time rather than binding it "
                   "as a default argument; if it binds it, this sweep had no effect.")
        out.append("")
    out.append(render_table(scores, sids))
    return "\n".join(out) + "\n"


def load_capretrieve_records(batches: Sequence[str], runs_dir: Path) -> list[RunRecord]:
    raw: list[RunRecord] = []
    for b in batches:
        text = (runs_dir / f"{b}.jsonl").read_text()
        raw += [RunRecord.model_validate_json(l) for l in text.splitlines() if l.strip()]
    return [
        r for r in final_records(raw)
        if r.router == "capretrieve" and r.error is None and r.requirements is not None
    ]


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Offline ablation and threshold sweep.")
    p.add_argument("--batch-id", required=True, nargs="+")
    p.add_argument("--scenarios-file", type=Path, default=DEFAULT_SCENARIOS)
    p.add_argument("--runs-dir", type=Path, default=DEFAULT_OUT_DIR)
    p.add_argument("--thresholds", default=",".join(map(str, DEFAULT_THRESHOLDS)))
    args = p.parse_args(argv)

    import capretrieve.planner.selection as selection
    from capretrieve.manifest.loader import load_manifest_dir
    from capretrieve.planner.models.requirements import QueryRequirements
    from capretrieve.planner.planner import plan
    from capretrieve.settings import get_settings

    manifests = list(load_manifest_dir(get_settings().config_dir).values())
    replayer = Replayer(plan, lambda d: QueryRequirements(**d), manifests)
    records = load_capretrieve_records(args.batch_id, args.runs_dir)
    name = "+".join(args.batch_id)

    report = run_all(
        replayer, records, load_expectations(args.scenarios_file), selection,
        [float(t) for t in args.thresholds.split(",") if t.strip()], name,
    )
    out_path = args.runs_dir.parent / f"{name}_replay.md"
    out_path.write_text(report)
    print(report)
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()