"""
Tests for trace/recorder.py — building a PlanTrace from a completed graph
state.
"""

from __future__ import annotations

from datetime import datetime, timezone

from capretrieve.contracts.result import Evidence
from capretrieve.planner.models.decision import ExclusionReason, SelectionDecision
from capretrieve.planner.models.plan import ExecutionPlan, PlanStep
from capretrieve.planner.models.requirements import QueryRequirements
from capretrieve.trace.recorder import build_trace


def _ev(source_id: str, uri: str) -> Evidence:
    return Evidence(
        source_id=source_id,
        content="content",
        score=1.0,
        uri=uri,
        retrieved_at=datetime.now(timezone.utc),
    )


def test_build_trace_includes_all_top_level_fields():
    plan = ExecutionPlan(
        steps=[PlanStep(connector_id="chroma", score=1.0)],
        decisions=[SelectionDecision(connector_id="chroma", admitted=True, score=1.0)],
    )
    state = {
        "query": "some query",
        "requirements": QueryRequirements(),
        "execution_plan": plan,
        "raw_evidence": [_ev("chroma", "u1")],
        "fused_evidence": [_ev("chroma", "u1")],
        "answer": "final answer",
    }

    trace = build_trace(state)

    assert trace.query == "some query"
    assert trace.requirements == QueryRequirements()
    assert trace.execution_plan == plan
    assert trace.answer == "final answer"


def test_execution_counts_evidence_per_selected_connector():
    plan = ExecutionPlan(
        steps=[
            PlanStep(connector_id="obsidian", score=1.0),
            PlanStep(connector_id="chroma", score=0.8),
        ],
        decisions=[
            SelectionDecision(connector_id="obsidian", admitted=True, score=1.0),
            SelectionDecision(connector_id="chroma", admitted=True, score=0.8),
        ],
    )
    state = {
        "query": "q",
        "requirements": QueryRequirements(),
        "execution_plan": plan,
        "raw_evidence": [
            _ev("obsidian", "o1"),
            _ev("obsidian", "o2"),
            _ev("chroma", "c1"),
        ],
        "fused_evidence": [],
        "answer": "",
    }

    trace = build_trace(state)
    counts = {r.connector_id: r.evidence_count for r in trace.execution}
    assert counts == {"obsidian": 2, "chroma": 1}


def test_selected_connector_with_zero_evidence_still_gets_a_record():
    """A connector that was queried but found nothing should still show
    up with evidence_count=0 — that's meaningful trace information, not
    something to silently drop."""
    plan = ExecutionPlan(
        steps=[PlanStep(connector_id="web_search", score=1.0)],
        decisions=[SelectionDecision(connector_id="web_search", admitted=True, score=1.0)],
    )
    state = {
        "query": "q",
        "requirements": QueryRequirements(),
        "execution_plan": plan,
        "raw_evidence": [],
        "fused_evidence": [],
        "answer": "",
    }

    trace = build_trace(state)
    assert len(trace.execution) == 1
    assert trace.execution[0].connector_id == "web_search"
    assert trace.execution[0].evidence_count == 0


def test_empty_plan_produces_empty_execution_list():
    plan = ExecutionPlan(
        steps=[],
        decisions=[
            SelectionDecision(
                connector_id="obsidian",
                admitted=False,
                exclusion_reason=ExclusionReason(
                    connector_id="obsidian", constraint="test", detail="test"
                ),
            )
        ],
    )
    state = {
        "query": "q",
        "requirements": QueryRequirements(),
        "execution_plan": plan,
        "raw_evidence": [],
        "fused_evidence": [],
        "answer": "no evidence available",
    }

    trace = build_trace(state)
    assert trace.execution == []
    assert trace.execution_plan.is_empty


def test_missing_optional_state_keys_default_gracefully():
    """raw_evidence/fused_evidence/answer might be absent from state if
    the graph short-circuited; build_trace should not crash."""
    plan = ExecutionPlan(steps=[], decisions=[])
    state = {
        "query": "q",
        "requirements": QueryRequirements(),
        "execution_plan": plan,
    }

    trace = build_trace(state)
    assert trace.fused_evidence == []
    assert trace.answer == ""


def test_answer_key_present_but_none_defaults_to_empty_string():
    """Regression test: state.get("answer", "") only falls back to ""
    when the KEY is missing, not when its value is None. synthesize_node
    can legitimately produce {"answer": None} if the LLM's response had
    a null message content (observed in real end-to-end testing when an
    OpenRouter response came back 200 OK with content=None) — build_trace
    must not crash on that, since PlanTrace.answer is a required str."""
    plan = ExecutionPlan(steps=[], decisions=[])
    state = {
        "query": "q",
        "requirements": QueryRequirements(),
        "execution_plan": plan,
        "raw_evidence": [],
        "fused_evidence": [],
        "answer": None,
    }

    trace = build_trace(state)
    assert trace.answer == ""