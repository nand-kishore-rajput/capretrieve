"""
graph/nodes/analyze.py — thin adapter: unpack state -> call
planner.analyzer -> pack state.

Node logic stays minimal by design (per the repo's "nodes ≤ 25 lines"
convention) — all real logic lives in planner/analyzer.py.
"""

from __future__ import annotations

import asyncio
from typing import Callable

from capretrieve.graph.state import GraphState
from capretrieve.llm.structured import CompletesText
from capretrieve.planner.analyzer import analyze


def make_analyze_node(client: CompletesText) -> Callable:
    async def analyze_node(state: GraphState) -> dict:
        # analyze() blocks on HTTP; keep it off the event loop
        requirements = await asyncio.to_thread(analyze, client, state["query"])
        return {"requirements": requirements}

    return analyze_node