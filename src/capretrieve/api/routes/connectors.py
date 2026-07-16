"""
api/routes/connectors.py — GET /connectors -> raw manifests.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from capretrieve.api.schemas import ConnectorsResponse

router = APIRouter()


@router.get("/connectors", response_model=ConnectorsResponse)
async def get_connectors(request: Request) -> ConnectorsResponse:
    registry = request.app.state.registry
    return ConnectorsResponse(connectors=registry.manifests())