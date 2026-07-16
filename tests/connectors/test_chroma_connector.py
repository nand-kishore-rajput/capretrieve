"""
Tests for connectors/chroma/connector.py — the Connector protocol
implementation over a Chroma collection.

Uses an injected chromadb.EphemeralClient() and a unique collection_name
per test — see test_chroma_ingest.py's docstring for the rationale
(PersistentClient hangs; separate EphemeralClient instances can still
share collection state by name per chroma-core/chroma#1976).
"""

from __future__ import annotations

import uuid
from pathlib import Path

import chromadb
import pytest

from capretrieve.connectors.chroma.connector import ChromaConnector
from capretrieve.connectors.chroma.ingest import ingest_corpus
from capretrieve.contracts.health import HealthState
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.manifest.loader import load_manifest_file

CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "corpus"
MANIFEST_PATH = Path(__file__).parents[2] / "configs" / "connectors" / "chroma.yaml"


@pytest.fixture
def chroma_client() -> chromadb.ClientAPI:
    return chromadb.EphemeralClient(settings=chromadb.config.Settings(anonymized_telemetry=False))


@pytest.fixture
def collection_name() -> str:
    return f"test_{uuid.uuid4().hex}"


@pytest.fixture
def ingested_connector(chroma_client, collection_name) -> ChromaConnector:
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name)
    manifest = load_manifest_file(MANIFEST_PATH)
    return ChromaConnector(manifest=manifest, client=chroma_client, collection_name=collection_name)


def test_manifest_matches_loaded_yaml(ingested_connector: ChromaConnector):
    manifest = load_manifest_file(MANIFEST_PATH)
    assert ingested_connector.manifest() == manifest
    assert ingested_connector.manifest().connector_id == "chroma"


async def test_health_ok_after_ingest(ingested_connector: ChromaConnector):
    health = await ingested_connector.health()
    assert health.state == HealthState.OK


async def test_health_degraded_for_empty_collection(chroma_client, collection_name):
    manifest = load_manifest_file(MANIFEST_PATH)
    empty_connector = ChromaConnector(
        manifest=manifest, client=chroma_client, collection_name=collection_name
    )
    health = await empty_connector.health()
    assert health.state == HealthState.DEGRADED


async def test_retrieve_returns_topically_relevant_doc_first(
    ingested_connector: ChromaConnector,
):
    result = await ingested_connector.retrieve(
        RetrievalRequest(query="intermittent fasting energy levels", top_k=2)
    )
    assert len(result.evidence) == 2
    top = result.evidence[0]
    assert "intermittent_fasting" in top.uri
    assert top.source_id == "chroma"
    assert top.score > 0


async def test_retrieve_respects_top_k(ingested_connector: ChromaConnector):
    result = await ingested_connector.retrieve(
        RetrievalRequest(query="ergonomics and sprints and fasting", top_k=1)
    )
    assert len(result.evidence) == 1


async def test_retrieve_top_k_larger_than_corpus_does_not_error(
    ingested_connector: ChromaConnector,
):
    result = await ingested_connector.retrieve(
        RetrievalRequest(query="anything", top_k=1000)
    )
    assert len(result.evidence) == 4  # capped at corpus size, no crash


async def test_retrieve_on_empty_collection_returns_no_evidence(chroma_client, collection_name):
    manifest = load_manifest_file(MANIFEST_PATH)
    empty_connector = ChromaConnector(
        manifest=manifest, client=chroma_client, collection_name=collection_name
    )
    result = await empty_connector.retrieve(RetrievalRequest(query="anything", top_k=5))
    assert result.evidence == []


def test_connector_requires_persist_dir_or_client():
    manifest = load_manifest_file(MANIFEST_PATH)
    with pytest.raises(ValueError):
        ChromaConnector(manifest=manifest)