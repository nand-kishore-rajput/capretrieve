"""
graph/nodes/plan.py — thin adapter: unpack state -> call planner.planner
-> pack state.

This is the wiring boundary between the registry and the planner: it's
allowed to import registry/ (graph/ is not subject to the planner's
import restriction), but it hands the pure planner only manifests, never
Connector instances — preserving the "planner never imports connectors or
registry" invariant on the planner's side of the boundary.
"""

from __future__ import annotations

from typing import Callable

from capretrieve.graph.state import GraphState
from capretrieve.planner.planner import plan as run_planner
from capretrieve.registry.static import Registry


def make_plan_node(registry: Registry) -> Callable:
    async def plan_node(state: GraphState) -> dict:
        manifests = list(registry.manifests().values())
        execution_plan = run_planner(manifests, state["requirements"])
        return {"execution_plan": execution_plan}

    return plan_node