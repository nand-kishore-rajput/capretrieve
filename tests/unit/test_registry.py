"""
Tests for registry/static.py: manifest loading, connector registration,
lookup, and the error paths that catch YAML/connector drift.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.result import RetrievalResult
from capretrieve.manifest.models import CapabilityManifest
from capretrieve.registry.errors import (
    ConnectorNotRegisteredError,
    ManifestConnectorMismatchError,
    UnknownConnectorIdError,
)
from capretrieve.registry.static import Registry, build_registry

CONFIG_DIR = Path(__file__).parents[2] / "configs" / "connectors"


class StubConnector:
    """Minimal Connector for testing registry behavior without a real
    retrieval backend."""

    def __init__(self, manifest: CapabilityManifest) -> None:
        self._manifest = manifest

    def manifest(self) -> CapabilityManifest:
        return self._manifest

    async def retrieve(self, req) -> RetrievalResult:
        return RetrievalResult(evidence=[])

    async def health(self) -> HealthStatus:
        return HealthStatus(state=HealthState.OK)


def _stub_manifest(connector_id: str = "ghost") -> CapabilityManifest:
    return CapabilityManifest(
        connector_id=connector_id,
        paradigm="keyword",
        freshness="static",
        privacy_tier="private_local",
        query_leaks_externally=False,
        scope="test manifest",
    )


def test_build_registry_loads_three_manifests():
    registry = build_registry(CONFIG_DIR)
    assert set(registry.manifests().keys()) == {"chroma", "obsidian", "web_search"}


def test_all_empty_before_registration():
    registry = build_registry(CONFIG_DIR)
    assert registry.all() == []


def test_register_and_retrieve_all_three():
    registry = build_registry(CONFIG_DIR)
    for manifest in registry.manifests().values():
        registry.register(StubConnector(manifest))

    ids = {c.manifest().connector_id for c in registry.all()}
    assert ids == {"chroma", "obsidian", "web_search"}


def test_get_returns_registered_connector():
    registry = build_registry(CONFIG_DIR)
    chroma_manifest = registry.manifests()["chroma"]
    registry.register(StubConnector(chroma_manifest))

    connector = registry.get("chroma")
    assert connector.manifest().connector_id == "chroma"


def test_get_unregistered_raises():
    registry = build_registry(CONFIG_DIR)
    with pytest.raises(ConnectorNotRegisteredError):
        registry.get("chroma")


def test_get_unknown_id_raises():
    registry = build_registry(CONFIG_DIR)
    with pytest.raises(ConnectorNotRegisteredError):
        registry.get("nonexistent")


def test_register_unknown_connector_id_raises():
    registry = build_registry(CONFIG_DIR)
    with pytest.raises(UnknownConnectorIdError):
        registry.register(StubConnector(_stub_manifest("ghost")))


def test_register_mismatched_manifest_raises():
    """A connector whose manifest() disagrees with the loaded YAML for the
    same connector_id should be rejected, not silently registered."""
    manifests = {"chroma": _stub_manifest("chroma")}  # deliberately wrong shape
    registry = Registry(manifests)

    # a connector reporting a *different* manifest for the same id
    drifted_manifest = _stub_manifest("chroma")
    drifted_manifest = drifted_manifest.model_copy(update={"scope": "different scope"})

    with pytest.raises(ManifestConnectorMismatchError):
        registry.register(StubConnector(drifted_manifest))