"""
RetrievalRequest — what the graph's fan-out node builds and passes to every
selected connector's retrieve(). Same shape regardless of which connector
receives it, so the graph doesn't need per-source special-casing.
"""

from __future__ import annotations

from pydantic import BaseModel


class RetrievalRequest(BaseModel):
    query: str

    top_k: int = 5

    filters: dict | None = None
    """Optional structured filters (e.g. tag/date constraints). Connectors
    that don't support filtering may ignore this field."""

    deadline_ms: int | None = None
    """Soft deadline for this retrieval call, propagated from the planner's
    latency budget. Enforced at the graph level in Phase 6."""