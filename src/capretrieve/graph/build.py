"""
graph/build.py — assembles the full LangGraph pipeline:

    analyze -> plan -> fan_out(retrieve) -> fuse -> synthesize

analyze and plan run in sequence; the plan's selected connectors are then
queried in parallel via LangGraph's Send mechanism (dynamic fan-out), fed
back into a single fuse step, then synthesized into one final answer.

analyzer_client and synthesis_client are injected separately (even though
both currently point at the same kind of LLM client) so that, in
principle, requirement extraction and answer synthesis could use
different models/configurations without any graph restructuring.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from capretrieve.graph.nodes.analyze import make_analyze_node
from capretrieve.graph.nodes.fuse import make_fuse_node
from capretrieve.graph.nodes.plan import make_plan_node
from capretrieve.graph.nodes.retrieve import (
    RETRIEVE_ONE_NODE_NAME,
    make_fan_out_router,
    make_retrieve_one_node,
)
from capretrieve.graph.nodes.synthesize import make_synthesize_node
from capretrieve.graph.state import GraphState
from capretrieve.llm.structured import CompletesText
from capretrieve.registry.static import Registry

ANALYZE = "analyze"
PLAN = "plan"
FUSE = "fuse"
SYNTHESIZE = "synthesize"


def build_graph(
    registry: Registry,
    analyzer_client: CompletesText,
    synthesis_client: CompletesText,
    default_top_k: int = 5,
    max_fused_items: int | None = None,
) -> CompiledStateGraph:
    builder = StateGraph(GraphState)

    builder.add_node(ANALYZE, make_analyze_node(analyzer_client))
    builder.add_node(PLAN, make_plan_node(registry))
    builder.add_node(RETRIEVE_ONE_NODE_NAME, make_retrieve_one_node(registry))
    builder.add_node(FUSE, make_fuse_node(max_items=max_fused_items))
    builder.add_node(SYNTHESIZE, make_synthesize_node(synthesis_client))

    builder.add_edge(START, ANALYZE)
    builder.add_edge(ANALYZE, PLAN)
    builder.add_conditional_edges(
        PLAN,
        make_fan_out_router(default_top_k=default_top_k),
        [RETRIEVE_ONE_NODE_NAME, FUSE],
    )
    builder.add_edge(RETRIEVE_ONE_NODE_NAME, FUSE)
    builder.add_edge(FUSE, SYNTHESIZE)
    builder.add_edge(SYNTHESIZE, END)

    return builder.compile()


def build_trace_graph(
    registry: Registry,
    analyzer_client: CompletesText,
    default_top_k: int = 5,
    max_fused_items: int | None = None,
) -> CompiledStateGraph:
    """
    Like build_graph but stops after fuse — no synthesis step, no second
    OpenRouter call. Used by the /trace endpoint to inspect routing
    decisions cheaply: only the analyzer LLM call runs, retrieval is real,
    but synthesis is skipped entirely.
    """
    builder = StateGraph(GraphState)

    builder.add_node(ANALYZE, make_analyze_node(analyzer_client))
    builder.add_node(PLAN, make_plan_node(registry))
    builder.add_node(RETRIEVE_ONE_NODE_NAME, make_retrieve_one_node(registry))
    builder.add_node(FUSE, make_fuse_node(max_items=max_fused_items))

    builder.add_edge(START, ANALYZE)
    builder.add_edge(ANALYZE, PLAN)
    builder.add_conditional_edges(
        PLAN,
        make_fan_out_router(default_top_k=default_top_k),
        [RETRIEVE_ONE_NODE_NAME, FUSE],
    )
    builder.add_edge(RETRIEVE_ONE_NODE_NAME, FUSE)
    builder.add_edge(FUSE, END)

    return builder.compile()