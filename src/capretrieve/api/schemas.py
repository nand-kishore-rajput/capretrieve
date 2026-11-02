"""
api/schemas.py — request/response models for the FastAPI routes.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from capretrieve.contracts.health import HealthStatus
from capretrieve.contracts.result import Evidence
from capretrieve.manifest.models import CapabilityManifest
from capretrieve.trace.models import PlanTrace


# Upper bound on per-connector results a caller may ask for; top_k is passed
# straight to Tavily (paid) and Chroma, so an unbounded value is a cost knob.
MAX_TOP_K = 50


class QueryRequest(BaseModel):
    query: str
    top_k: int = Field(5, ge=1, le=MAX_TOP_K)


class QueryResponse(BaseModel):
    answer: str
    evidence: list[Evidence]
    plan_trace: PlanTrace


class ConnectorsResponse(BaseModel):
    connectors: dict[str, CapabilityManifest]


class ConnectorHealthEntry(BaseModel):
    connector_id: str
    health: HealthStatus


class HealthResponse(BaseModel):
    connectors: list[ConnectorHealthEntry]