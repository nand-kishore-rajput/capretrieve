"""
graph/nodes/synthesize.py — thin adapter: unpack state -> call
generation.synthesize -> pack state.
"""

from __future__ import annotations

from typing import Callable

from capretrieve.generation.synthesize import synthesize
from capretrieve.graph.state import GraphState
from capretrieve.llm.structured import CompletesText


def make_synthesize_node(client: CompletesText) -> Callable:
    async def synthesize_node(state: GraphState) -> dict:
        answer = synthesize(client, state["query"], state.get("fused_evidence", []))
        return {"answer": answer}

    return synthesize_node