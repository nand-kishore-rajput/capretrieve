"""
graph/nodes/retrieve.py — dynamic parallel fan-out over the connectors
selected by the plan.

Two pieces:
  - make_fan_out_router: a conditional-edge function. An empty plan
    routes straight to "fuse" (skipping retrieval entirely — there's
    nothing to retrieve). A non-empty plan returns one Send("retrieve_one",
    ...) per selected connector, which LangGraph executes in parallel.
    When requirements.relational and requirements.seed_entity are both
    set, this also builds a {"seed_note": ..., "depth": ...} filter and
    attaches it to every branch — connectors that don't understand
    "seed_note" (Chroma, web search) simply ignore it; ObsidianConnector
    uses it to switch from keyword search to graph traversal.
  - make_retrieve_one_node: the per-branch node. Looks up the actual
    Connector instance from the registry and calls its retrieve(). This
    is the only node that touches connectors/ directly. A connector that
    raises contributes no evidence and a retrieval_errors entry instead,
    so the other branches' evidence still reaches fuse and the trace.
"""

from __future__ import annotations

from typing import Callable

from langgraph.types import Send

from capretrieve.contracts.request import RetrievalRequest
from capretrieve.graph.state import GraphState, RetrieveOneInput
from capretrieve.registry.static import Registry

FUSE_NODE_NAME = "fuse"
RETRIEVE_ONE_NODE_NAME = "retrieve_one"

DEFAULT_TRAVERSAL_DEPTH = 1


def _build_retrieval_filters(state: GraphState) -> dict | None:
    """Derive RetrievalRequest.filters from the query's requirements.
    Currently only produces the seed_note/depth pair for a relational
    query with a named seed_entity; returns None otherwise."""
    requirements = state.get("requirements")
    if requirements is None:
        return None
    if requirements.relational and requirements.seed_entity:
        return {"seed_note": requirements.seed_entity, "depth": DEFAULT_TRAVERSAL_DEPTH}
    return None


def make_fan_out_router(default_top_k: int = 5) -> Callable:
    def route_to_retrievals(state: GraphState) -> str | list[Send]:
        execution_plan = state["execution_plan"]
        if execution_plan.is_empty:
            return FUSE_NODE_NAME

        top_k = state.get("top_k", default_top_k)
        filters = _build_retrieval_filters(state)

        return [
            Send(
                RETRIEVE_ONE_NODE_NAME,
                RetrieveOneInput(
                    connector_id=step.connector_id,
                    query=state["query"],
                    top_k=top_k,
                    filters=filters,
                ),
            )
            for step in execution_plan.steps
        ]

    return route_to_retrievals


def make_retrieve_one_node(registry: Registry) -> Callable:
    async def retrieve_one_node(send_state: RetrieveOneInput) -> dict:
        connector_id = send_state["connector_id"]
        connector = registry.get(connector_id)
        request = RetrievalRequest(
            query=send_state["query"],
            top_k=send_state["top_k"],
            filters=send_state.get("filters"),
        )
        try:
            result = await connector.retrieve(request)
        except Exception as exc:  # noqa: BLE001 - one bad source must not sink the query
            error = f"{type(exc).__name__}: {exc}"
            return {"retrieval_errors": [{"connector_id": connector_id, "error": error}]}
        return {"raw_evidence": list(result.evidence)}

    return retrieve_one_node