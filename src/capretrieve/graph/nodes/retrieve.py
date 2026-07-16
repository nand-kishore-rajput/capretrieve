"""
graph/nodes/retrieve.py — dynamic parallel fan-out over the connectors
selected by the plan.

Two pieces:
  - make_fan_out_router: a conditional-edge function. An empty plan
    routes straight to "fuse" (skipping retrieval entirely — there's
    nothing to retrieve). A non-empty plan returns one Send("retrieve_one",
    ...) per selected connector, which LangGraph executes in parallel.
  - make_retrieve_one_node: the per-branch node. Looks up the actual
    Connector instance from the registry and calls its retrieve(). This
    is the only node that touches connectors/ directly.
"""

from __future__ import annotations

from typing import Callable

from langgraph.types import Send

from capretrieve.contracts.request import RetrievalRequest
from capretrieve.graph.state import GraphState, RetrieveOneInput
from capretrieve.registry.static import Registry

FUSE_NODE_NAME = "fuse"
RETRIEVE_ONE_NODE_NAME = "retrieve_one"


def make_fan_out_router(default_top_k: int = 5) -> Callable:
    def route_to_retrievals(state: GraphState) -> str | list[Send]:
        execution_plan = state["execution_plan"]
        if execution_plan.is_empty:
            return FUSE_NODE_NAME

        top_k = state.get("top_k", default_top_k)
        return [
            Send(
                RETRIEVE_ONE_NODE_NAME,
                RetrieveOneInput(
                    connector_id=step.connector_id, query=state["query"], top_k=top_k
                ),
            )
            for step in execution_plan.steps
        ]

    return route_to_retrievals


def make_retrieve_one_node(registry: Registry) -> Callable:
    async def retrieve_one_node(send_state: RetrieveOneInput) -> dict:
        connector = registry.get(send_state["connector_id"])
        request = RetrievalRequest(query=send_state["query"], top_k=send_state["top_k"])
        result = await connector.retrieve(request)
        return {"raw_evidence": list(result.evidence)}

    return retrieve_one_node