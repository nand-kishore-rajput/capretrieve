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

All calls to ingest_corpus pass HashingEmbeddingFunction() explicitly so
tests are independent of the EMBEDDING_MODEL env var, which may be set
by load_dotenv() reading the project's .env file at import time even
when the test runner sets EMBEDDING_MODEL= in the shell.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import chromadb
import pytest

from capretrieve.connectors.chroma.embeddings import HashingEmbeddingFunction
from capretrieve.connectors.chroma.ingest import ingest_corpus

CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "data" / "corpus"

# Number of .md files currently in the corpus fixture directory.
# Update this if corpus files are added or removed.
CORPUS_COUNT = len(list(CORPUS_DIR.glob("*.md")))


@pytest.fixture
def chroma_client() -> chromadb.ClientAPI:
    return chromadb.EphemeralClient(settings=chromadb.config.Settings(anonymized_telemetry=False))


@pytest.fixture
def collection_name() -> str:
    return f"test_{uuid.uuid4().hex}"


@pytest.fixture
def ef() -> HashingEmbeddingFunction:
    """Explicit embedding function — never depends on EMBEDDING_MODEL env var."""
    return HashingEmbeddingFunction()


def test_ingest_requires_persist_dir_or_client():
    with pytest.raises(ValueError):
        ingest_corpus(CORPUS_DIR)


def test_ingest_returns_count_of_ingested_docs(chroma_client, collection_name, ef):
    count = ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name,
                          embedding_function=ef)
    assert count == CORPUS_COUNT


def test_ingest_populates_collection(chroma_client, collection_name, ef):
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name,
                  embedding_function=ef)
    collection = chroma_client.get_or_create_collection(
        collection_name, embedding_function=ef
    )
    assert collection.count() == CORPUS_COUNT


def test_ingest_is_idempotent(chroma_client, collection_name, ef):
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name,
                  embedding_function=ef)
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name,
                  embedding_function=ef)
    collection = chroma_client.get_or_create_collection(
        collection_name, embedding_function=ef
    )
    assert collection.count() == CORPUS_COUNT


def test_ingest_empty_corpus_dir_returns_zero(tmp_path, chroma_client, collection_name, ef):
    empty_corpus = tmp_path / "empty_corpus"
    empty_corpus.mkdir()
    count = ingest_corpus(empty_corpus, client=chroma_client, collection_name=collection_name,
                          embedding_function=ef)
    assert count == 0


def test_ingest_stores_source_path_metadata(chroma_client, collection_name, ef):
    ingest_corpus(CORPUS_DIR, client=chroma_client, collection_name=collection_name,
                  embedding_function=ef)
    collection = chroma_client.get_or_create_collection(
        collection_name, embedding_function=ef
    )
    # rag_survey.md is one of the large corpus files present in all fixture sets
    got = collection.get(ids=["rag_survey"])
    assert got["metadatas"][0]["source_path"].endswith("rag_survey.md")