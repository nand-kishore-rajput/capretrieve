"""
Tests for connectors/chroma/connector.py — the Connector protocol
implementation over a Chroma collection.

Uses an injected chromadb.EphemeralClient() and a unique collection_name
per test — see test_chroma_ingest.py's docstring for the rationale
(PersistentClient hangs; separate EphemeralClient instances can still
share collection state by name per chroma-core/chroma#1976).

Two corpora are used deliberately:
- CORPUS_DIR (fixtures/data/corpus) for contract behaviour (health, top_k
  capping). Assertions derive counts from the directory, never hard-code them,
  so swapping the fixture corpus doesn't break these tests.
- A tiny tmp_path corpus with disjoint vocabularies for the ranking test.
  HashingEmbeddingFunction is bag-of-words hashing, so ranking is only
  meaningful when the query shares real tokens with exactly one doc. Pinning
  a ranking against the shared fixture corpus would assert hash-collision noise.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import chromadb
import pytest

from capretrieve.connectors.chroma.connector import ChromaConnector
from capretrieve.connectors.chroma.embeddings import HashingEmbeddingFunction
from capretrieve.connectors.chroma.ingest import ingest_corpus
from capretrieve.contracts.health import HealthState
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.manifest.loader import load_manifest_file

CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "corpus"
MANIFEST_PATH = Path(__file__).parents[2] / "configs" / "connectors" / "chroma.yaml"

RANKING_DOCS = {
    "volcanoes.md": "# Volcanoes\n\nMagma erupts through the crust. Lava, ash and "
    "pyroclastic flows follow a volcanic eruption.",
    "baking.md": "# Baking bread\n\nFlour, yeast, water and salt. Knead the dough, "
    "let it proof, then bake in a hot oven.",
    "sailing.md": "# Sailing\n\nTrim the mainsail, watch the wind, tack upwind "
    "and keep the boat balanced on the keel.",
}


@pytest.fixture
def chroma_client() -> chromadb.ClientAPI:
    return chromadb.EphemeralClient(
        settings=chromadb.config.Settings(anonymized_telemetry=False)
    )


@pytest.fixture
def collection_name() -> str:
    return f"test_{uuid.uuid4().hex}"


@pytest.fixture
def corpus_size() -> int:
    return len(list(CORPUS_DIR.glob("*.md")))


def _make_connector(client, collection_name, ef) -> ChromaConnector:
    return ChromaConnector(
        manifest=load_manifest_file(MANIFEST_PATH),
        client=client,
        collection_name=collection_name,
        embedding_function=ef,
    )


@pytest.fixture
def ingested_connector(chroma_client, collection_name) -> ChromaConnector:
    ef = HashingEmbeddingFunction()
    ingest_corpus(
        CORPUS_DIR,
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=ef,
    )
    return _make_connector(chroma_client, collection_name, ef)


@pytest.fixture
def ranking_connector(chroma_client, collection_name, tmp_path) -> ChromaConnector:
    for name, text in RANKING_DOCS.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    ef = HashingEmbeddingFunction()
    ingest_corpus(
        tmp_path,
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=ef,
    )
    return _make_connector(chroma_client, collection_name, ef)


@pytest.fixture
def empty_connector(chroma_client, collection_name) -> ChromaConnector:
    return _make_connector(chroma_client, collection_name, HashingEmbeddingFunction())


def test_fixture_corpus_is_not_empty(corpus_size: int):
    assert corpus_size > 0, f"no .md files in {CORPUS_DIR}"


def test_manifest_matches_loaded_yaml(ingested_connector: ChromaConnector):
    manifest = load_manifest_file(MANIFEST_PATH)
    assert ingested_connector.manifest() == manifest
    assert ingested_connector.manifest().connector_id == "chroma"


async def test_health_ok_after_ingest(ingested_connector: ChromaConnector):
    health = await ingested_connector.health()
    assert health.state == HealthState.OK


async def test_health_degraded_for_empty_collection(empty_connector: ChromaConnector):
    health = await empty_connector.health()
    assert health.state == HealthState.DEGRADED


async def test_retrieve_returns_topically_relevant_doc_first(
    ranking_connector: ChromaConnector,
):
    result = await ranking_connector.retrieve(
        RetrievalRequest(query="volcanic eruption magma lava ash", top_k=2)
    )
    assert len(result.evidence) == 2
    top = result.evidence[0]
    assert top.uri.endswith("volcanoes.md")
    assert top.source_id == "chroma"
    assert top.score > result.evidence[1].score


async def test_retrieve_respects_top_k(ingested_connector: ChromaConnector):
    result = await ingested_connector.retrieve(
        RetrievalRequest(query="language models retrieval", top_k=1)
    )
    assert len(result.evidence) == 1


async def test_retrieve_top_k_larger_than_corpus_does_not_error(
    ingested_connector: ChromaConnector, corpus_size: int
):
    result = await ingested_connector.retrieve(
        RetrievalRequest(query="anything", top_k=corpus_size + 1000)
    )
    assert len(result.evidence) == corpus_size  # capped at corpus size, no crash


async def test_retrieve_on_empty_collection_returns_no_evidence(
    empty_connector: ChromaConnector,
):
    result = await empty_connector.retrieve(RetrievalRequest(query="anything", top_k=5))
    assert result.evidence == []


def test_connector_requires_persist_dir_or_client():
    manifest = load_manifest_file(MANIFEST_PATH)
    with pytest.raises(ValueError):
        ChromaConnector(manifest=manifest)