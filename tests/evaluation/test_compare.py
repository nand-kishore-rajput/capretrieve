"""compare.py tests: hand-built records, no LLM."""

from __future__ import annotations

from datetime import datetime, timezone

from capretrieve.evaluation.compare import (
    Expectation,
    analyzer_stability,
    build_cells,
    final_records,
    hard_block_rates,
    is_correct,
    load_expectations,
    render,
)
from capretrieve.evaluation.records import RunRecord

S1 = Expectation("S1", "active", frozenset({"obsidian", "chroma"}), frozenset({"web_search"}))
S2 = Expectation("S2", "deferred", frozenset({"obsidian", "web_search"}), frozenset())
EXPS = {"S1": S1, "S2": S2}


def rec(router="capretrieve", sid="S1", i=0, selected=(), excluded=None, error=None, req=None, invalid=()):
    return RunRecord(
        batch_id="b", scenario_id=sid, router=router, run_idx=i, model="m",
        selected=list(selected), excluded=excluded or {}, invalid=list(invalid),
        requirements=req, error=error, latency_ms=1.0, timestamp=datetime.now(timezone.utc),
    )


def test_correctness_needs_all_includes_and_no_excludes():
    assert is_correct(rec(selected=["obsidian", "chroma"]), S1)
    assert not is_correct(rec(selected=["chroma"]), S1)  # missing obsidian
    assert not is_correct(rec(selected=["obsidian", "chroma", "web_search"]), S1)  # leak
    assert not is_correct(rec(selected=["obsidian", "chroma"], error="boom"), S1)


def test_final_records_prefers_latest_success_over_failures():
    fail = rec(error="429")
    ok = rec(selected=["chroma"])
    later_fail = rec(error="429 again")
    assert final_records([fail, ok])[0].error is None
    assert final_records([ok, later_fail])[0].error is None  # success not overwritten
    assert final_records([fail, later_fail])[0].error == "429 again"


def test_cells_accuracy_violations_consistency():
    records = [
        rec("tool_description", i=0, selected=["web_search"]),
        rec("tool_description", i=1, selected=["web_search"]),
        rec("tool_description", i=2, selected=["obsidian", "chroma"]),
        rec("tool_description", i=3, error="boom"),
    ]
    c = build_cells(records, EXPS)[("S1", "tool_description")]
    assert (c.n, c.correct, c.violations, c.errors) == (4, 1, 2, 1)
    assert c.consistency == 2 / 3  # errors excluded from the plan distribution


def test_hard_block_rate_and_stability():
    records = [
        rec(i=0, selected=["obsidian", "chroma"], excluded={"web_search": "privacy_leak"},
            req={"privacy_sensitivity": "confidential", "relational": False}),
        rec(i=1, selected=["chroma"], excluded={"web_search": "privacy_leak"},
            req={"privacy_sensitivity": "personal", "relational": False}),
    ]
    assert hard_block_rates(records, EXPS)[("S1", "web_search")] == (1.0, "privacy_leak")
    stab = analyzer_stability(records)["S1"]
    assert stab["relational"] == (1.0, "false")
    assert stab["privacy_sensitivity"][0] == 0.5


def test_render_marks_gaps_and_excludes_them_from_overall():
    records = [
        rec(i=0, selected=["obsidian", "chroma"]),
        rec(sid="S2", i=0, selected=["obsidian"]),  # wrong, but a known gap
        rec("tool_description", i=0, selected=["web_search"], invalid=["google"]),
        rec("tool_description", i=1, selected=["web_search"]),
    ]
    md = render("b", records, EXPS)
    assert "S2 (known gap)" in md
    assert "**100%** (1/1)" in md  # capretrieve overall counts S1 only
    assert "50% (1/2)" in md  # tool_description invalid-id rate
    assert "Held-out" not in md  # no held-out rows when there are none


S6 = Expectation(
    "S6", "held_out", frozenset(), frozenset({"web_search"}),
    must_include_any=frozenset({"obsidian", "chroma"}),
)


def test_must_include_any_needs_one_local_source_and_no_web():
    assert is_correct(rec(sid="S6", selected=["chroma"]), S6)
    assert is_correct(rec(sid="S6", selected=["obsidian"]), S6)
    assert not is_correct(rec(sid="S6", selected=[]), S6)  # empty plan is not a pass
    assert not is_correct(rec(sid="S6", selected=["chroma", "web_search"]), S6)


def test_held_out_only_batch_has_no_empty_original_row():
    md = render("b", [rec(sid="S6", i=0, selected=["chroma"])], {**EXPS, "S6": S6})
    assert "Original scenarios" not in md and "All scored" not in md
    assert "**Held-out scenarios** | **100%** (1/1)" in md


def test_final_records_keeps_same_run_idx_from_different_batches():
    a = rec(i=0, selected=["chroma"])
    b = rec(i=0, selected=["obsidian"]).model_copy(update={"batch_id": "other"})
    assert len(final_records([a, b])) == 2


def test_held_out_scored_and_reported_separately():
    exps = {**EXPS, "S6": S6}
    records = [
        rec(i=0, selected=["obsidian", "chroma"]),  # S1 correct
        rec(sid="S6", i=0, selected=["web_search"]),  # S6 wrong
    ]
    md = render("b", records, exps)
    assert "S6 (held-out)" in md
    assert "**Original scenarios** | **100%** (1/1)" in md
    assert "**Held-out scenarios** | **0%** (0/1)" in md
    assert "**All scored scenarios** | **50%** (1/2)" in md


def test_load_expectations(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text(
        "scenarios:\n"
        "  - id: S4\n    query: q\n    must_include: [obsidian]\n"
        "    must_exclude:\n      - {connector_id: chroma, reason: x}\n    status: active\n"
    )
    e = load_expectations(f)["S4"]
    assert e.must_include == {"obsidian"} and e.must_exclude == {"chroma"} and e.active
    assert e.must_include_any == frozenset() and not e.held_out