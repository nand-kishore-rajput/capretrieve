"""
Tests for connectors/chroma/ingest.py — corpus ingestion into a Chroma
collection.

Uses an injected chromadb.EphemeralClient() rather than a real
PersistentClient against tmp_path — see ingest.py's docstring for why
(PersistentClient's per-path SQLite caching + background threads are a
known source of hangs when many instances are created within one pytest
process, independent of network conditions).

Each test also uses its own unique collection_name. Chroma has a known
issue (chroma-core/chroma#1976) where separate EphemeralClient instances
within the same process can still share collection state keyed by name —
i.e. client-instance boundaries alone don't guarantee isolation. Unique
names per test sidestep that regardless of the underlying cause.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import chromadb
import pytest

from capretrieve.connectors.chroma.embeddings import HashingEmbeddingFunction
from capretrieve.connectors.chroma.ingest import ingest_corpus

CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "corpus"


@pytest.fixture
def chroma_client() -> chromadb.ClientAPI:
    return chromadb.EphemeralClient(settings=chromadb.config.Settings(anonymized_telemetry=False))


@pytest.fixture
def collection_name() -> str:
    return f"test_{uuid.uuid4().hex}"


def test_ingest_requires_persist_dir_or_client():
    with pytest.raises(ValueError):
        ingest_corpus(CORPUS_DIR)


def test_ingest_returns_count_of_ingested_docs(chroma_client, collection_name):
    count = ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name)
    assert count == 4


def test_ingest_populates_collection(chroma_client, collection_name):
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name)
    collection = chroma_client.get_or_create_collection(
        collection_name, embedding_function=HashingEmbeddingFunction()
    )
    assert collection.count() == 4


def test_ingest_is_idempotent(chroma_client, collection_name):
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name)
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name)
    collection = chroma_client.get_or_create_collection(
        collection_name, embedding_function=HashingEmbeddingFunction()
    )
    assert collection.count() == 4


def test_ingest_empty_corpus_dir_returns_zero(tmp_path, chroma_client, collection_name):
    empty_corpus = tmp_path / "empty_corpus"
    empty_corpus.mkdir()
    count = ingest_corpus(empty_corpus, client=chroma_client, collection_name=collection_name)
    assert count == 0


def test_ingest_stores_source_path_metadata(chroma_client, collection_name):
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name)
    collection = chroma_client.get_or_create_collection(
        collection_name, embedding_function=HashingEmbeddingFunction()
    )
    got = collection.get(ids=["intermittent_fasting_overview"])
    assert got["metadatas"][0]["source_path"].endswith(
        "intermittent_fasting_overview.md"
    )