"""
Tests for graph/nodes/retrieve.py — the fan-out router and its
seed_note/depth filter construction from QueryRequirements.

This is the exact wiring that was missing before: a relational query
with a seed_entity needs to actually produce a {"seed_note": ...} filter
that reaches RetrievalRequest, or graph-traversal-capable connectors
silently fall back to keyword search regardless of paradigm routing.
"""

from __future__ import annotations

from langgraph.types import Send

from capretrieve.graph.nodes.retrieve import (
    FUSE_NODE_NAME,
    RETRIEVE_ONE_NODE_NAME,
    _build_retrieval_filters,
    make_fan_out_router,
)
from capretrieve.planner.models.decision import SelectionDecision
from capretrieve.planner.models.plan import ExecutionPlan, PlanStep
from capretrieve.planner.models.requirements import QueryRequirements


def _plan(*connector_ids: str) -> ExecutionPlan:
    return ExecutionPlan(
        steps=[PlanStep(connector_id=cid, score=1.0) for cid in connector_ids],
        decisions=[
            SelectionDecision(connector_id=cid, admitted=True, score=1.0)
            for cid in connector_ids
        ],
    )


def test_build_filters_none_when_not_relational():
    state = {"requirements": QueryRequirements(relational=False, seed_entity="x")}
    assert _build_retrieval_filters(state) is None


def test_build_filters_none_when_relational_but_no_seed_entity():
    state = {"requirements": QueryRequirements(relational=True, seed_entity=None)}
    assert _build_retrieval_filters(state) is None


def test_build_filters_produces_seed_note_when_both_present():
    state = {
        "requirements": QueryRequirements(relational=True, seed_entity="project retrospective")
    }
    filters = _build_retrieval_filters(state)
    assert filters == {"seed_note": "project retrospective", "depth": 1}


def test_build_filters_none_when_requirements_missing():
    assert _build_retrieval_filters({}) is None


def test_router_empty_plan_routes_to_fuse():
    router = make_fan_out_router()
    state = {
        "execution_plan": ExecutionPlan(steps=[], decisions=[]),
        "query": "q",
        "requirements": QueryRequirements(),
    }
    assert router(state) == FUSE_NODE_NAME


def test_router_non_empty_plan_returns_one_send_per_step():
    router = make_fan_out_router()
    state = {
        "execution_plan": _plan("obsidian", "chroma"),
        "query": "q",
        "requirements": QueryRequirements(),
        "top_k": 3,
    }
    sends = router(state)
    assert len(sends) == 2
    assert all(isinstance(s, Send) for s in sends)
    assert {s.node for s in sends} == {RETRIEVE_ONE_NODE_NAME}


def test_router_attaches_seed_note_filter_to_every_branch():
    """Even in a multi-connector plan, the seed_note filter is attached
    to every Send — connectors that don't understand it just ignore it
    (see RetrieveOneInput's docstring)."""
    router = make_fan_out_router()
    state = {
        "execution_plan": _plan("obsidian", "chroma"),
        "query": "what links to X",
        "requirements": QueryRequirements(relational=True, seed_entity="X"),
        "top_k": 3,
    }
    sends = router(state)
    for send in sends:
        assert send.arg["filters"] == {"seed_note": "X", "depth": 1}


def test_router_no_filters_for_non_relational_query():
    router = make_fan_out_router()
    state = {
        "execution_plan": _plan("chroma"),
        "query": "summarize my notes",
        "requirements": QueryRequirements(relational=False),
        "top_k": 3,
    }
    sends = router(state)
    assert sends[0].arg["filters"] is None


def test_router_uses_default_top_k_when_absent_from_state():
    router = make_fan_out_router(default_top_k=7)
    state = {
        "execution_plan": _plan("chroma"),
        "query": "q",
        "requirements": QueryRequirements(),
    }
    sends = router(state)
    assert sends[0].arg["top_k"] == 7