"""
api/routes/trace.py — POST /trace -> routing trace only, no synthesis.

Uses the trace_graph (analyze -> plan -> retrieve -> fuse, stopping before
synthesize) so only one OpenRouter call fires (the analyzer). Useful for
debugging routing decisions and running evaluation queries cheaply.

GET /trace/view?query=... -> the same trace rendered as an HTML page,
openable straight from the browser address bar. Runs the full graph so
the page includes the synthesized answer.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from capretrieve.api.schemas import QueryRequest
from capretrieve.trace.recorder import build_trace
from capretrieve.trace.render import render_html

router = APIRouter()

# The page is static HTML with one inline <style>; it needs nothing else.
TRACE_VIEW_CSP = "default-src 'none'; style-src 'unsafe-inline'"


@router.post("/trace")
async def run_trace(req: QueryRequest, request: Request) -> JSONResponse:
    # trace_graph stops after fuse — no synthesis LLM call
    trace_graph = request.app.state.trace_graph
    state = await trace_graph.ainvoke({"query": req.query, "top_k": req.top_k})
    trace = build_trace(state)
    return JSONResponse(content=trace.model_dump(mode="json"))


@router.get("/trace/view", response_class=HTMLResponse)
async def view_trace(request: Request, query: str, top_k: int = 5) -> HTMLResponse:
    # full graph (not trace_graph) so the page's Answer section is filled in
    graph = request.app.state.graph
    state = await graph.ainvoke({"query": query, "top_k": top_k})
    trace = build_trace(state)
    return HTMLResponse(
        content=render_html(trace),
        headers={"Content-Security-Policy": TRACE_VIEW_CSP},
    )
