"""
api/routes/trace.py — POST /trace -> routing trace only, no synthesis.

Uses the trace_graph (analyze -> plan -> retrieve -> fuse, stopping before
synthesize) so only one OpenRouter call fires (the analyzer). Useful for
debugging routing decisions and running evaluation queries cheaply.

GET /trace/view?query=...&token=... -> the same trace rendered as an HTML
page, openable straight from the browser address bar. Runs the full graph
so the page includes the synthesized answer.

Because it's a GET that spends LLM/search credits, any web page could
trigger it (e.g. an <img> pointing at localhost) while the API is
reachable. It therefore requires the TRACE_VIEW_TOKEN value as `token`,
checked before any LLM call, and is disabled when no token is configured.
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse

from capretrieve.api.schemas import MAX_TOP_K, QueryRequest
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
async def view_trace(
    request: Request,
    query: str,
    top_k: int = Query(5, ge=1, le=MAX_TOP_K),
    token: str = "",
) -> HTMLResponse:
    expected = request.app.state.trace_view_token
    if not expected or not secrets.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="valid token required")

    # full graph (not trace_graph) so the page's Answer section is filled in
    graph = request.app.state.graph
    state = await graph.ainvoke({"query": query, "top_k": top_k})
    trace = build_trace(state)
    return HTMLResponse(
        content=render_html(trace),
        headers={"Content-Security-Policy": TRACE_VIEW_CSP},
    )
