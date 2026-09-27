"""
Turns a runner log into the evaluation tables. No LLM calls; re-run freely.

    python -m capretrieve.evaluation.compare --batch-id main
    python -m capretrieve.evaluation.compare --batch-id main heldout   # combined

Reads   reports/runs/<batch>.jsonl  and  fixtures/scenarios.yaml
Writes  reports/<batch>_summary.md  (and prints it)

Scoring rules (per run):
- correct  = every must_include connector selected
             AND at least one must_include_any connector selected (if given)
             AND no must_exclude connector selected.
             Invalid (hallucinated) ids are ignored for correctness but
             counted separately.
- A run whose final attempt errored counts as incorrect, never as an empty
  plan. For each (scenario, router, run_idx) the LATEST successful record
  wins; earlier failed attempts from resumed batches are ignored.
- status: active    -> scored, part of the original design set (S1-S5)
          held_out  -> scored, reported separately (written after the
                       analyzer prompt and scoring were frozen)
          anything else (e.g. deferred) -> known gap, not scored overall

Tables:
1. Routing accuracy per scenario x router.
2. Violations: share of runs that selected a must_exclude connector
   (for S1 this is the privacy-leak rate).
3. Consistency: share of runs agreeing with the router's most common plan.
4. Hard-block rate (capretrieve only): share of runs where each
   must_exclude connector was removed by a hard constraint, not just
   out-scored.
5. Analyzer stability (capretrieve only): per requirement field, share of
   runs agreeing with the most common value.
6. Invalid-id rate for LLM routers.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from capretrieve.evaluation.records import RunRecord
from capretrieve.evaluation.runner import DEFAULT_OUT_DIR, DEFAULT_SCENARIOS

ROUTER_ORDER = ["capretrieve", "keyword", "tool_description", "tool_description_policy"]


@dataclass(frozen=True)
class Expectation:
    id: str
    status: str
    must_include: frozenset[str]
    must_exclude: frozenset[str]
    must_include_any: frozenset[str] = frozenset()

    @property
    def held_out(self) -> bool:
        return self.status == "held_out"

    @property
    def active(self) -> bool:
        """Scored (original or held-out), as opposed to a known gap."""
        return self.status in ("active", "held_out")


def load_expectations(path: Path) -> dict[str, Expectation]:
    data = yaml.safe_load(path.read_text())
    items = data["scenarios"] if isinstance(data, dict) else data
    return {
        str(s["id"]): Expectation(
            id=str(s["id"]),
            status=s.get("status", "active"),
            must_include=frozenset(s.get("must_include") or []),
            must_exclude=frozenset(e["connector_id"] for e in s.get("must_exclude") or []),
            must_include_any=frozenset(s.get("must_include_any") or []),
        )
        for s in items
    }


def final_records(records: Iterable[RunRecord]) -> list[RunRecord]:
    """One record per (scenario, router, run_idx): latest success, else latest failure.

    Records must be in log order (the runner appends chronologically).
    """
    best: dict[tuple[str, str, int], RunRecord] = {}
    for r in records:
        key = (r.batch_id, r.scenario_id, r.router, r.run_idx)
        cur = best.get(key)
        # a later record replaces the current one unless it's a failure
        # arriving after a success
        if cur is None or r.error is None or cur.error is not None:
            best[key] = r
    return sorted(best.values(), key=lambda r: (r.router, r.scenario_id, r.run_idx))


def is_correct(r: RunRecord, exp: Expectation) -> bool:
    if r.error is not None:
        return False
    sel = set(r.selected)
    return (
        exp.must_include <= sel
        and (not exp.must_include_any or bool(exp.must_include_any & sel))
        and not (exp.must_exclude & sel)
    )


def violates(r: RunRecord, exp: Expectation) -> bool:
    return r.error is None and bool(exp.must_exclude & set(r.selected))


@dataclass
class Cell:
    n: int = 0
    correct: int = 0
    violations: int = 0
    errors: int = 0
    invalid_runs: int = 0
    plans: Counter = field(default_factory=Counter)

    @property
    def accuracy(self) -> float:
        return self.correct / self.n if self.n else 0.0

    @property
    def consistency(self) -> float:
        ok = sum(self.plans.values())
        return self.plans.most_common(1)[0][1] / ok if ok else 0.0


def build_cells(records: Sequence[RunRecord], exps: dict[str, Expectation]) -> dict[tuple[str, str], Cell]:
    cells: dict[tuple[str, str], Cell] = defaultdict(Cell)
    for r in records:
        exp = exps.get(r.scenario_id)
        if exp is None:
            continue
        c = cells[(r.scenario_id, r.router)]
        c.n += 1
        c.correct += is_correct(r, exp)
        c.violations += violates(r, exp)
        if r.error is not None:
            c.errors += 1
            continue
        c.invalid_runs += bool(r.invalid)
        c.plans[tuple(sorted(r.selected))] += 1
    return cells


def analyzer_stability(records: Sequence[RunRecord]) -> dict[str, dict[str, tuple[float, str]]]:
    """scenario -> field -> (agreement with modal value, modal value as text)."""
    by_scenario: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        if r.router == "capretrieve" and r.error is None and r.requirements is not None:
            by_scenario[r.scenario_id].append(r.requirements)
    out: dict[str, dict[str, tuple[float, str]]] = {}
    for sid, reqs in by_scenario.items():
        fields = sorted({k for q in reqs for k in q})
        out[sid] = {}
        for f in fields:
            counts = Counter(json.dumps(q.get(f), sort_keys=True) for q in reqs)
            value, n = counts.most_common(1)[0]
            out[sid][f] = (n / len(reqs), value)
    return out


def hard_block_rates(
    records: Sequence[RunRecord], exps: dict[str, Expectation]
) -> dict[tuple[str, str], tuple[float, str]]:
    """(scenario, connector) -> (share of capretrieve runs hard-blocked, most common constraint)."""
    out = {}
    for sid, exp in exps.items():
        runs = [r for r in records if r.router == "capretrieve" and r.scenario_id == sid and r.error is None]
        if not runs:
            continue
        for cid in sorted(exp.must_exclude):
            constraints = Counter(r.excluded[cid] for r in runs if cid in r.excluded)
            blocked = sum(constraints.values())
            top = constraints.most_common(1)[0][0] if constraints else "-"
            out[(sid, cid)] = (blocked / len(runs), top)
    return out


# ── rendering ────────────────────────────────────────────────────────────


def _pct(x: float) -> str:
    return f"{100 * x:.0f}%"


def _table(header: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def render(batch_id: str, records: Sequence[RunRecord], exps: dict[str, Expectation]) -> str:
    cells = build_cells(records, exps)
    present = {r for _, r in cells}
    routers = [r for r in ROUTER_ORDER if r in present] + sorted(present - set(ROUTER_ORDER))
    scenarios = [s for s in exps if any((s, r) in cells for r in routers)]

    def label(sid: str) -> str:
        if exps[sid].held_out:
            return f"{sid} (held-out)"
        return sid if exps[sid].active else f"{sid} (known gap)"

    def per_router(metric) -> list[list[str]]:
        rows = []
        for sid in scenarios:
            row = [label(sid)]
            for rt in routers:
                c = cells.get((sid, rt))
                row.append(metric(c) if c else "-")
            rows.append(row)
        return rows

    out = [f"# Evaluation summary: batch `{batch_id}`", ""]
    n_by_router = {rt: max((c.n for (s, r), c in cells.items() if r == rt), default=0) for rt in routers}
    out.append("Runs per scenario: " + ", ".join(f"{rt} n={n_by_router[rt]}" for rt in routers))
    errs = sum(c.errors for c in cells.values())
    if errs:
        out.append(f"\n**{errs} run(s) ended in an error and are scored as incorrect.**")

    out += ["", "## 1. Routing accuracy", ""]
    rows = per_router(lambda c: f"{_pct(c.accuracy)} ({c.correct}/{c.n})")
    has_orig = any(exps[s].active and not exps[s].held_out for s in scenarios)
    has_held = any(exps[s].held_out for s in scenarios)
    groups = []
    if has_orig:
        groups.append(("Original scenarios", lambda e: e.active and not e.held_out))
    if has_held:
        groups.append(("Held-out scenarios", lambda e: e.held_out))
    if has_orig and has_held:
        groups.append(("All scored scenarios", lambda e: e.active))
    totals = []
    for title, keep in groups:
        row = [f"**{title}**"]
        for rt in routers:
            cs = [cells[(s, rt)] for s in scenarios if keep(exps[s]) and (s, rt) in cells]
            tot, cor = sum(c.n for c in cs), sum(c.correct for c in cs)
            row.append(f"**{_pct(cor / tot) if tot else '-'}** ({cor}/{tot})")
        totals.append(row)
    out.append(_table(["Scenario", *routers], [*rows, *totals]))

    out += ["", "## 2. Violations: a must_exclude source was selected", ""]
    out.append("For S1 this is the privacy-leak rate: the query was sent to web_search.")
    out.append("")
    out.append(_table(["Scenario", *routers], per_router(lambda c: f"{_pct(c.violations / c.n)} ({c.violations}/{c.n})")))

    out += ["", "## 3. Consistency: runs agreeing with the most common plan", ""]
    out.append(_table(
        ["Scenario", *routers],
        per_router(lambda c: f"{_pct(c.consistency)} → {'+'.join(c.plans.most_common(1)[0][0]) or '∅'}" if c.plans else "-"),
    ))

    hb = hard_block_rates(records, exps)
    if hb:
        out += ["", "## 4. CapRetrieve hard blocks", ""]
        out.append("Share of runs where a must_exclude source was removed by a hard constraint "
                   "(rather than simply scoring too low).")
        out.append("")
        out.append(_table(
            ["Scenario", "Source", "Hard-blocked", "Constraint"],
            [[label(s), cid, _pct(rate), f"`{con}`"] for (s, cid), (rate, con) in hb.items()],
        ))

    stab = analyzer_stability(records)
    if stab:
        out += ["", "## 5. Analyzer stability (CapRetrieve)", ""]
        out.append("Share of runs whose requirement field matched the most common value "
                   "(most common value in brackets). Fields below 100% are marked.")
        out.append("")
        fields = sorted({f for per in stab.values() for f in per})
        rows = []
        for sid in scenarios:
            if sid not in stab:
                continue
            row = [label(sid)]
            for f in fields:
                agree, val = stab[sid].get(f, (0.0, "-"))
                mark = "" if agree == 1.0 else " ⚠"
                row.append(f"{_pct(agree)} [{val}]{mark}")
            rows.append(row)
        out.append(_table(["Scenario", *fields], rows))

    llm_routers = [rt for rt in routers if n_by_router[rt] > 1 and rt != "capretrieve"]
    if llm_routers:
        out += ["", "## 6. Hallucinated source ids (LLM baselines)", ""]
        rows = []
        for rt in llm_routers:
            cs = [c for (s, r), c in cells.items() if r == rt]
            inv, ok = sum(c.invalid_runs for c in cs), sum(c.n - c.errors for c in cs)
            rows.append([rt, f"{_pct(inv / ok) if ok else '-'} ({inv}/{ok})"])
        out.append(_table(["Router", "Runs with an invalid id"], rows))

    return "\n".join(out) + "\n"


def main(argv: Sequence[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="Summarise an evaluation batch.")
    p.add_argument(
        "--batch-id", required=True, nargs="+",
        help="one or more batch ids; several are combined into one summary",
    )
    p.add_argument("--scenarios-file", type=Path, default=DEFAULT_SCENARIOS)
    p.add_argument("--runs-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = p.parse_args(argv)

    raw: list[RunRecord] = []
    for batch in args.batch_id:
        log = args.runs_dir / f"{batch}.jsonl"
        raw += [RunRecord.model_validate_json(l) for l in log.read_text().splitlines() if l.strip()]
    name = "+".join(args.batch_id)
    summary = render(name, final_records(raw), load_expectations(args.scenarios_file))
    out_path = args.runs_dir.parent / f"{name}_summary.md"
    out_path.write_text(summary)
    print(summary)
    print(f"written: {out_path}")


if __name__ == "__main__":
    main()