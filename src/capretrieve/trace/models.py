"""
trace/models.py — PlanTrace: the full, human-readable decision path for
one query.

This is "the demo artifact" per the phase plan — the thing a person shows
to explain why the system did what it did, not a logging format. It
wraps the ExecutionPlan (which already carries requirements-derived
candidates, hard-block reasons, soft scores, and the final selection)
with what happened AFTER planning: per-connector execution results and
the fused evidence that fed the final answer.
"""

from __future__ import annotations

from pydantic import BaseModel

from capretrieve.contracts.result import Evidence
from capretrieve.planner.models.plan import ExecutionPlan
from capretrieve.planner.models.requirements import QueryRequirements


class ConnectorExecutionRecord(BaseModel):
    """What actually happened when a selected connector was queried."""

    connector_id: str
    evidence_count: int
    error: str | None = None
    """Set when the connector raised during retrieve(); None on success."""


class PlanTrace(BaseModel):
    """
    The complete trace for one query:
      query -> requirements -> execution_plan (candidates, blocks+reason,
      scores, selection) -> execution (per-connector results) ->
      fused_evidence -> answer.
    """

    query: str
    requirements: QueryRequirements
    execution_plan: ExecutionPlan
    execution: list[ConnectorExecutionRecord]
    fused_evidence: list[Evidence]
    answer: str