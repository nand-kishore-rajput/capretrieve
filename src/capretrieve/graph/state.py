"""
GraphState — the shared state schema flowing through the LangGraph
pipeline: analyze -> plan -> fan_out(retrieve) -> fuse -> synthesize.

Uses a TypedDict + Annotated reducer (rather than the Pydantic models used
elsewhere in this project) because that's LangGraph's standard pattern for
accumulating results from a dynamic, parallel fan-out (raw_evidence is
appended to by every parallel retrieve_one invocation via operator.add).
This lives in graph/, not planner/models/, so it isn't subject to the
planner's "pure data" architectural invariant — orchestration state is a
different concern from the planner's data contract.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from capretrieve.contracts.result import Evidence
from capretrieve.planner.models.plan import ExecutionPlan
from capretrieve.planner.models.requirements import QueryRequirements


class GraphState(TypedDict, total=False):
    query: str
    top_k: int

    requirements: QueryRequirements
    execution_plan: ExecutionPlan

    # Populated by parallel retrieve_one invocations (one per selected
    # connector via Send); operator.add concatenates each branch's list
    # rather than overwriting, which is what makes fan-out -> fan-in work.
    raw_evidence: Annotated[list[Evidence], operator.add]

    fused_evidence: list[Evidence]
    answer: str


class RetrieveOneInput(TypedDict):
    """The per-branch state sent to retrieve_one via Send — deliberately
    smaller than the full GraphState, since each parallel branch only
    needs to know which connector to query and with what request."""

    connector_id: str
    query: str
    top_k: int