"""
Corpus ingestion for the Chroma connector.

One-time (or re-run-on-change) step that loads fixtures/data/corpus/*.md
into a Chroma collection. Deliberately separate from connector.py:
ingestion is a build/setup concern, retrieval is a runtime concern, and
conflating them would make the connector harder to reason about and test.

Anonymized telemetry is explicitly disabled on every client constructed
here. ChromaDB's default client phones home to PostHog on client/
collection events; that's both an unwanted network dependency for an
offline-first connector and a bad look for a project whose S1 scenario is
specifically about not leaking things externally without being told to.

The chromadb client is injectable (`client=`). Real usage should pass
persist_dir and let this function build a PersistentClient. Tests should
inject a chromadb.EphemeralClient() instead: PersistentClient's SQLite
backend caches one client per path in a process-wide registry and manages
background threads for persistence — repeatedly constructing/discarding
PersistentClient instances against many different tmp_path directories
within a single pytest process is a known source of hangs and lock
contention in chromadb (unrelated to network conditions). EphemeralClient
is pure in-memory and avoids that whole class of issue.
"""

from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.api.types import EmbeddingFunction

from capretrieve.connectors.chroma.embeddings import HashingEmbeddingFunction

DEFAULT_COLLECTION_NAME = "capretrieve_corpus"


def _default_client(persist_dir: Path) -> chromadb.ClientAPI:
    return chromadb.PersistentClient(
        path=str(persist_dir),
        settings=chromadb.config.Settings(anonymized_telemetry=False),
    )


def ingest_corpus(
    corpus_dir: Path,
    persist_dir: Path | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    embedding_function: EmbeddingFunction | None = None,
    client: chromadb.ClientAPI | None = None,
) -> int:
    """
    Load every .md/.txt file in corpus_dir into a Chroma collection.
    Re-running is idempotent — existing ids are upserted, not duplicated,
    so ingestion can safely run on every container start.

    Either persist_dir or client must be provided. If client is given,
    persist_dir is ignored — this is the test-time path (inject an
    EphemeralClient). If only persist_dir is given, a PersistentClient is
    built against it — this is the real, on-disk usage path.

    Returns the number of documents ingested. Returns 0 (without touching
    the collection) if corpus_dir has no matching files.
    """
    paths = sorted(p for p in corpus_dir.iterdir() if p.suffix in {".md", ".txt"})
    if not paths:
        return 0

    if client is None:
        if persist_dir is None:
            raise ValueError("ingest_corpus requires either persist_dir or client")
        client = _default_client(persist_dir)

    ef = embedding_function if embedding_function is not None else HashingEmbeddingFunction()
    collection = client.get_or_create_collection(collection_name, embedding_function=ef)

    ids = [p.stem for p in paths]
    documents = [p.read_text(encoding="utf-8") for p in paths]
    metadatas = [{"source_path": str(p)} for p in paths]

    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    return len(paths)


if __name__ == "__main__":
    import sys

    corpus_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("fixtures/data/corpus")
    persist_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".chroma")
    count = ingest_corpus(corpus_dir, persist_dir=persist_dir)
    print(
        f"Ingested {count} documents into {persist_dir} "
        f"(collection={DEFAULT_COLLECTION_NAME})"
    )