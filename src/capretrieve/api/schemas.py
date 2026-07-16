"""
api/schemas.py — request/response models for the FastAPI routes.
"""

from __future__ import annotations

from pydantic import BaseModel

from capretrieve.contracts.health import HealthStatus
from capretrieve.contracts.result import Evidence
from capretrieve.manifest.models import CapabilityManifest
from capretrieve.trace.models import PlanTrace


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


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