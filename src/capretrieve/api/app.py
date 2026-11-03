"""
api/app.py — FastAPI app factory.

create_app takes a Registry and two LLM clients via dependency injection
— the same pattern used throughout this project (connectors, planner,
graph) — so the app is fully testable with real local connectors + fake
external clients, without a running server or real network access. Real
production wiring (reading API keys from env, building real connectors,
running corpus ingestion) is a bootstrap concern that lives outside this
factory, not inside it.
"""

from __future__ import annotations

from fastapi import FastAPI

from capretrieve.api.routes import connectors as connectors_route
from capretrieve.api.routes import demo as demo_route
from capretrieve.api.routes import health as health_route
from capretrieve.api.routes import query as query_route
from capretrieve.api.routes import trace as trace_route
from capretrieve.graph.build import build_graph, build_trace_graph
from capretrieve.llm.structured import CompletesText
from capretrieve.registry.static import Registry


def create_app(
    registry: Registry,
    analyzer_client: CompletesText,
    synthesis_client: CompletesText,
    default_top_k: int = 5,
    max_fused_items: int | None = None,
    trace_view_token: str | None = None,
) -> FastAPI:
    app = FastAPI(title="CapRetrieve")

    app.state.registry = registry
    # None disables GET /trace/view (see api/routes/trace.py)
    app.state.trace_view_token = trace_view_token
    app.state.graph = build_graph(
        registry,
        analyzer_client,
        synthesis_client,
        default_top_k=default_top_k,
        max_fused_items=max_fused_items,
    )
    app.state.trace_graph = build_trace_graph(
        registry,
        analyzer_client,
        default_top_k=default_top_k,
        max_fused_items=max_fused_items,
    )

    app.include_router(query_route.router)
    app.include_router(connectors_route.router)
    app.include_router(health_route.router)
    app.include_router(trace_route.router)
    app.include_router(demo_route.router)

    return app