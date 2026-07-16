"""
api/routes/query.py — POST /query -> {answer, evidence[], plan_trace}.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from capretrieve.api.schemas import QueryRequest, QueryResponse
from capretrieve.trace.recorder import build_trace

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def run_query(req: QueryRequest, request: Request) -> QueryResponse:
    graph = request.app.state.graph
    state = await graph.ainvoke({"query": req.query, "top_k": req.top_k})

    trace = build_trace(state)
    return QueryResponse(
        answer=state.get("answer", ""),
        evidence=state.get("fused_evidence", []),
        plan_trace=trace,
    )