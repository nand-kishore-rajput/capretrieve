"""
api/routes/trace.py — POST /trace -> routing trace only, no synthesis.

Uses the trace_graph (analyze -> plan -> retrieve -> fuse, stopping before
synthesize) so only one OpenRouter call fires (the analyzer). Useful for
debugging routing decisions and running evaluation queries cheaply.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from capretrieve.api.schemas import QueryRequest
from capretrieve.trace.recorder import build_trace

router = APIRouter()


@router.post("/trace")
async def run_trace(req: QueryRequest, request: Request) -> JSONResponse:
    # trace_graph stops after fuse — no synthesis LLM call
    trace_graph = request.app.state.trace_graph
    state = await trace_graph.ainvoke({"query": req.query, "top_k": req.top_k})
    trace = build_trace(state)
    return JSONResponse(content=trace.model_dump(mode="json"))