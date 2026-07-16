"""
api/routes/health.py — GET /health -> aggregated per-connector health.

Calls each registered connector's real health() (see each connector's own
docstring for what that checks — e.g. Chroma/Obsidian check local
reachability, the web connector checks configuration only to avoid
burning API quota on every health check).
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from capretrieve.api.schemas import ConnectorHealthEntry, HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request) -> HealthResponse:
    registry = request.app.state.registry

    entries = []
    for connector in registry.all():
        status = await connector.health()
        entries.append(
            ConnectorHealthEntry(
                connector_id=connector.manifest().connector_id, health=status
            )
        )

    return HealthResponse(connectors=entries)