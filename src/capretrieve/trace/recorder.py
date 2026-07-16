"""
trace/recorder.py — builds a PlanTrace from a completed GraphState (the
dict returned by graph.ainvoke()).
"""

from __future__ import annotations

from capretrieve.graph.state import GraphState
from capretrieve.trace.models import ConnectorExecutionRecord, PlanTrace


def build_trace(state: GraphState) -> PlanTrace:
    """
    Turn a completed graph invocation's state into a PlanTrace.

    Every connector the plan actually selected gets a
    ConnectorExecutionRecord — including one with evidence_count=0 if it
    was queried but returned nothing, since "queried this source and
    found nothing" is itself meaningful trace information, not something
    to omit.
    """
    execution_plan = state["execution_plan"]
    raw_evidence = state.get("raw_evidence", [])

    counts: dict[str, int] = {step.connector_id: 0 for step in execution_plan.steps}
    for evidence_item in raw_evidence:
        counts[evidence_item.source_id] = counts.get(evidence_item.source_id, 0) + 1

    execution = [
        ConnectorExecutionRecord(connector_id=connector_id, evidence_count=count)
        for connector_id, count in counts.items()
    ]

    return PlanTrace(
        query=state["query"],
        requirements=state["requirements"],
        execution_plan=execution_plan,
        execution=execution,
        fused_evidence=state.get("fused_evidence", []),
        # state.get("answer", "") only falls back to "" when the KEY is
        # missing, not when its value is None — and synthesize_node can
        # legitimately produce {"answer": None} if the LLM response had
        # a null content field. `or ""` coerces both cases uniformly.
        answer=state.get("answer") or "",
    )