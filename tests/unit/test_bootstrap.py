"""
Tests for bootstrap.py — real connector wiring (fully offline: Obsidian
is a real local vault, Chroma uses an injected EphemeralClient rather
than a real on-disk PersistentClient, WebSearchConnector construction is
lazy/keyless-safe) and the fail-fast behavior when OPENROUTER_API_KEY is
missing.

Every test injects chroma_client explicitly (a chromadb.EphemeralClient)
rather than letting build_default_registry construct a real
PersistentClient. This is not optional here: constructing many real
PersistentClients across many tests in one pytest process is a
documented chromadb hang/lock issue (see connectors/chroma/ingest.py's
docstring and bootstrap.py's build_default_registry docstring) — an
earlier version of this file didn't inject a client and hung partway
through the suite for exactly that reason.

Does NOT test build_default_graph/build_default_app's actual LLM calls —
those need a real OPENROUTER_API_KEY and real network access, neither of
which is available in this environment. See bootstrap.py's module
docstring.
"""

from __future__ import annotations

import chromadb
import pytest

from capretrieve.bootstrap import build_default_app, build_default_graph, build_default_registry
from capretrieve.connectors.chroma.embeddings import HashingEmbeddingFunction
from capretrieve.contracts.health import HealthState
from capretrieve.settings import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        llm_api_key=None,
        web_search_api_key=None,
        chroma_persist_dir=tmp_path / "chroma",
    )


@pytest.fixture
def chroma_client() -> chromadb.ClientAPI:
    return chromadb.EphemeralClient(settings=chromadb.config.Settings(anonymized_telemetry=False))


@pytest.fixture
def ef() -> HashingEmbeddingFunction:
    """Explicit embedding function — never depends on EMBEDDING_MODEL env var."""
    return HashingEmbeddingFunction()


def test_build_default_registry_registers_all_three_connectors(settings, chroma_client, ef):
    registry = build_default_registry(settings, chroma_client=chroma_client, embedding_function=ef)
    ids = {c.manifest().connector_id for c in registry.all()}
    assert ids == {"obsidian", "chroma", "web_search"}


async def test_build_default_registry_chroma_is_ingested(settings, chroma_client, ef):
    registry = build_default_registry(settings, chroma_client=chroma_client, embedding_function=ef)
    chroma = registry.get("chroma")
    health = await chroma.health()
    assert health.state == HealthState.OK


def test_build_default_registry_obsidian_uses_configured_vault_dir(settings, chroma_client, ef):
    registry = build_default_registry(settings, chroma_client=chroma_client, embedding_function=ef)
    obsidian = registry.get("obsidian")
    assert obsidian._vault_dir == settings.vault_dir


def test_build_default_graph_raises_without_openrouter_key(settings, chroma_client, ef):
    registry = build_default_registry(settings, chroma_client=chroma_client, embedding_function=ef)
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        build_default_graph(settings, registry=registry)


def test_build_default_app_raises_without_openrouter_key(settings):
    with pytest.raises(RuntimeError, match="LLM_API_KEY"):
        build_default_app(settings)


def test_build_default_graph_accepts_a_prebuilt_registry(settings, chroma_client, ef, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "fake-key-not-actually-called")
    settings.llm_api_key = "fake-key-not-actually-called"

    registry = build_default_registry(settings, chroma_client=chroma_client, embedding_function=ef)
    graph = build_default_graph(settings, registry=registry)
    assert graph is not None