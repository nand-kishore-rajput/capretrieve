"""
graph/nodes/fuse.py — thin adapter: unpack state -> call fusion.merge ->
pack state.
"""

from __future__ import annotations

from typing import Callable

from capretrieve.fusion.merge import fuse
from capretrieve.graph.state import GraphState


def make_fuse_node(max_items: int | None = None) -> Callable:
    async def fuse_node(state: GraphState) -> dict:
        raw_evidence = state.get("raw_evidence", [])
        fused = fuse(raw_evidence, max_items=max_items)
        return {"fused_evidence": fused}

    return fuse_node