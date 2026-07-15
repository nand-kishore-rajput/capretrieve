"""
Static connector registry — an explicit dict, deliberately not a plugin
system.

Loads CapabilityManifests from configs/connectors/*.yaml and pairs each one
with a registered Connector instance. No dynamic discovery, no entry points.
Adding a new source means: write a YAML manifest, implement a Connector,
call register() once at startup. Nothing here is auto-detected.

The planner (planner/) calls registry.all() to get every candidate
connector + manifest. It must never import connectors/ directly — that
boundary is enforced by tests/architecture/test_planner_imports.py.
"""

from __future__ import annotations

from pathlib import Path

from capretrieve.contracts.protocol import Connector
from capretrieve.manifest.loader import load_manifest_dir
from capretrieve.manifest.models import CapabilityManifest
from capretrieve.registry.errors import (
    ConnectorNotRegisteredError,
    ManifestConnectorMismatchError,
    UnknownConnectorIdError,
)


class Registry:
    """
    Holds registered connectors alongside their manifests.

    Manifests are loaded once (typically from configs/connectors/) and
    connectors are registered against them explicitly. This split matters:
    Phase 1 can test manifest loading and registry lookup end-to-end using
    stub connectors, before any real connector exists.
    """

    def __init__(self, manifests: dict[str, CapabilityManifest]) -> None:
        self._manifests = manifests
        self._connectors: dict[str, Connector] = {}

    def register(self, connector: Connector) -> None:
        """Register a connector instance. Its manifest().connector_id must
        already have a loaded manifest with the same id — this catches the
        common mistake of a YAML file and a connector class disagreeing
        about their own identity."""
        connector_id = connector.manifest().connector_id

        if connector_id not in self._manifests:
            raise UnknownConnectorIdError(connector_id, known=set(self._manifests))

        if connector.manifest() != self._manifests[connector_id]:
            raise ManifestConnectorMismatchError(connector_id)

        self._connectors[connector_id] = connector

    def all(self) -> list[Connector]:
        """Every registered connector. Order follows registration order."""
        return list(self._connectors.values())

    def get(self, connector_id: str) -> Connector:
        try:
            return self._connectors[connector_id]
        except KeyError as exc:
            raise ConnectorNotRegisteredError(
                connector_id, registered=set(self._connectors)
            ) from exc

    def manifests(self) -> dict[str, CapabilityManifest]:
        """All loaded manifests, including ones with no connector registered
        yet. Useful for Phase 1 testing before real connectors exist."""
        return dict(self._manifests)


def build_registry(config_dir: Path) -> Registry:
    """Load manifests from config_dir and return an empty Registry ready
    for connector registration. Callers (typically api/app.py at startup
    in later phases) then call registry.register(connector) for each
    real connector."""
    manifests = load_manifest_dir(config_dir)
    return Registry(manifests)