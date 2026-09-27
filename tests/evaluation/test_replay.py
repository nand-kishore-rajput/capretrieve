"""replay.py tests. A small fake planner with the same shape of rules as the
real one: privacy hard block, paradigm hard block, additive scores, relative
threshold read from a module at call time."""

from __future__ import annotations

from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace

from pydantic import BaseModel

from capretrieve.evaluation.compare import Expectation
from capretrieve.evaluation.records import RunRecord
from capretrieve.evaluation.replay import (
    MASKED,
    Replayer,
    mask_manifests,
    patched_threshold,
    run_all,
    score,
)


class Manifest(BaseModel):
    connector_id: str
    paradigm: str
    freshness: str
    privacy_tier: str
    query_leaks_externally: bool


class Reqs(BaseModel):
    privacy_sensitivity: str = "none"
    relational: bool = False
    needs_freshness: str = "any"
    paradigm_hint: str | None = None


MANIFESTS = [
    Manifest(connector_id="chroma", paradigm="dense_semantic", freshness="index_time",
             privacy_tier="private_local", query_leaks_externally=False),
    Manifest(connector_id="obsidian", paradigm="graph_traversal", freshness="live",
             privacy_tier="private_local", query_leaks_externally=False),
    Manifest(connector_id="web_search", paradigm="keyword", freshness="live",
             privacy_tier="public_external", query_leaks_externally=True),
]

selection = ModuleType("fake_selection")
selection.RELATIVE_THRESHOLD = 0.8


def fake_plan(manifests, req):
    decisions, scores = [], {}
    for m in manifests:
        reason = None
        if req.privacy_sensitivity != "none" and m.query_leaks_externally:
            reason = "privacy_leak"
        elif req.relational and m.paradigm != "graph_traversal":
            reason = "paradigm_mismatch"
        if reason:
            decisions.append(SimpleNamespace(
                connector_id=m.connector_id,
                exclusion_reason=SimpleNamespace(constraint=reason)))
            continue
        s = (1.0 if m.paradigm == req.paradigm_hint else 0.0)
        s += 0.3 if req.needs_freshness != "any" and m.freshness == "live" else 0.0
        scores[m.connector_id] = s
        decisions.append(SimpleNamespace(connector_id=m.connector_id, exclusion_reason=None))
    top = max(scores.values(), default=0.0)
    cutoff = top * (1 - selection.RELATIVE_THRESHOLD)  # read at call time
    chosen = [c for c, s in scores.items() if top > 0 and s >= cutoff]
    return SimpleNamespace(selected_connector_ids=chosen, decisions=decisions)


S1 = Expectation("S1", "active", frozenset({"obsidian", "chroma"}), frozenset({"web_search"}))
S9 = Expectation("S9", "held_out", frozenset({"web_search"}), frozenset())
EXPS = {"S1": S1, "S9": S9}


def rec(sid, i, req: dict, selected):
    return RunRecord(
        batch_id="b", scenario_id=sid, router="capretrieve", run_idx=i, model="m",
        selected=selected, requirements=req, latency_ms=1.0,
        timestamp=datetime.now(timezone.utc),
    )


S1_REQ = {"privacy_sensitivity": "confidential", "needs_freshness": "recent",
          "paradigm_hint": "dense_semantic", "relational": False}
S9_REQ = {"privacy_sensitivity": "none", "needs_freshness": "recent",
          "paradigm_hint": "keyword", "relational": False}


def replayer():
    return Replayer(fake_plan, lambda d: Reqs(**d), MANIFESTS)


def logged():
    r = replayer()
    base = [rec("S1", 0, S1_REQ, []), rec("S9", 0, S9_REQ, [])]
    # make the "log" exactly what the planner produces, as a real batch would
    return [b.model_copy(update={"selected": n.selected}) for b, n in zip(base, r.run(base))]


def test_baseline_replay_reproduces_log_and_scores():
    records = logged()
    s = score("base", replayer().run(records), records, EXPS)
    assert s.changed == 0 and s.errors == 0
    assert s.per_scenario == {"S1": (1, 1), "S9": (1, 1)}
    assert s.original == (1, 1) and s.held_out == (1, 1)


def test_masking_query_leaks_externally_lets_the_leak_through():
    masked = mask_manifests(MANIFESTS, "query_leaks_externally")
    assert all(m.query_leaks_externally is False for m in masked)
    assert MANIFESTS[2].query_leaks_externally is True  # originals untouched

    records = logged()
    out = replayer().run(records, manifests=masked)
    assert "web_search" in out[0].selected
    s = score("x", out, records, EXPS)
    assert s.violations == 1 and s.per_scenario["S1"] == (0, 1)


def test_masking_a_string_field_uses_sentinel():
    assert {m.freshness for m in mask_manifests(MANIFESTS, "freshness")} == {MASKED}


def test_requirement_reset_changes_plan():
    records = logged()
    out = replayer().run(records, requirement_update={"needs_freshness": "any"})
    assert out[0].selected == ["chroma"]  # obsidian loses its freshness bonus
    assert score("x", out, records, EXPS).per_scenario["S1"] == (0, 1)


def test_threshold_patch_is_restored_and_takes_effect():
    records = logged()
    with patched_threshold(selection, 0.5):
        tight = replayer().run(records)
    assert selection.RELATIVE_THRESHOLD == 0.8
    assert tight[0].selected == ["chroma"]  # 0.3 < 1.0 * (1 - 0.5)


def test_crashing_variant_is_counted_as_error_not_raised():
    def boom(ms, req):
        raise ValueError("bad enum")

    records = logged()
    out = Replayer(boom, lambda d: Reqs(**d), MANIFESTS).run(records)
    s = score("x", out, records, EXPS)
    assert s.errors == 2 and s.per_scenario["S1"] == (0, 1)


def test_run_all_report_sections_and_determinism():
    md = run_all(replayer(), logged(), EXPS, selection, [0.0, 0.5], "b")
    assert "Determinism check passed" in md
    assert "− query_leaks_externally" in md and "− needs_freshness" in md
    assert "0.8 (current)" in md
    assert "identical results" not in md


def test_run_all_warns_when_log_does_not_match():
    records = [r.model_copy(update={"selected": ["web_search"]}) for r in logged()]
    assert "Warning: unmodified replay differs" in run_all(
        replayer(), records, EXPS, selection, [0.5], "b"
    )


def test_error_message_is_shown_under_the_table():
    from capretrieve.evaluation.replay import render_table

    def boom(ms, req):
        raise ValueError("bad enum")

    records = logged()
    s = score("− paradigm", Replayer(boom, lambda d: Reqs(**d), MANIFESTS).run(records), records, EXPS)
    md = render_table([s], ["S1", "S9"])
    assert "`− paradigm`: 2 run(s) failed, first error: `ValueError: bad enum`" in md


def test_masked_value_behaves_like_an_enum_member():
    import enum

    class Paradigm(str, enum.Enum):
        GRAPH = "graph_traversal"

    m = mask_manifests(MANIFESTS, "paradigm")[0].paradigm
    assert m.value == MASKED and m.name == MASKED
    assert m != Paradigm.GRAPH and m != "graph_traversal"
    assert m not in {p.value for p in Paradigm}