"""
Connector — the structural contract every source implementation must
satisfy.

This is a Protocol (structural typing), not a base class: a connector in
connectors/ just needs to match this shape, no inheritance required. The
registry stores instances typed as Connector; the graph's retrieve node
calls .retrieve() on whatever the planner selected without knowing or
caring whether it's backed by chromadb, an Obsidian vault parser, or a
web search SDK.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from capretrieve.contracts.health import HealthStatus
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.contracts.result import RetrievalResult
from capretrieve.manifest.models import CapabilityManifest


@runtime_checkable
class Connector(Protocol):
    def manifest(self) -> CapabilityManifest:
        """Return this connector's declared capabilities. Should be cheap
        and side-effect free — called frequently by the registry and
        planner."""
        ...

    async def retrieve(self, req: RetrievalRequest) -> RetrievalResult:
        """Execute a retrieval against this source and return normalized
        Evidence. All connector-specific logic (client calls, parsing,
        traversal) is hidden behind this single method."""
        ...

    async def health(self) -> HealthStatus:
        """Report whether this connector is currently usable. Used by
        graph/policies.py (Phase 6) to decide whether to re-plan around
        a degraded or unreachable source."""
        ...