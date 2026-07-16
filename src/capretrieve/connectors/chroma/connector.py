"""
ChromaConnector — implements the Connector protocol over a ChromaDB
collection.

Ingestion (loading fixtures/data/corpus/ into the collection) is handled
separately by ingest.py; this connector only queries an already-ingested
collection at query time. If the collection is empty, retrieve() returns
no evidence and health() reports degraded, rather than either connector
silently triggering ingestion as a side effect of a query.

Anonymized telemetry is explicitly disabled (see ingest.py for the same
setting and rationale).

The chromadb client is injectable (`client=`), same rationale as
ingest.py: real usage should pass persist_dir; tests should inject a
chromadb.EphemeralClient() to avoid PersistentClient's SQLite-backed
per-path client caching and background threads, which are a known source
of hangs when many instances are created/discarded within one process.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import chromadb
from chromadb.api.types import EmbeddingFunction

from capretrieve.connectors.chroma.embeddings import HashingEmbeddingFunction
from capretrieve.connectors.chroma.ingest import DEFAULT_COLLECTION_NAME
from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.contracts.result import Evidence, RetrievalResult
from capretrieve.manifest.models import CapabilityManifest


class ChromaConnector:
    """
    manifest is injected (same pattern as ObsidianConnector) so it's
    guaranteed identical to whatever registry/static.py loaded from
    configs/connectors/chroma.yaml.

    Either persist_dir or client must be provided. If client is given,
    persist_dir is ignored.
    """

    def __init__(
        self,
        manifest: CapabilityManifest,
        persist_dir: Path | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedding_function: EmbeddingFunction | None = None,
        client: chromadb.ClientAPI | None = None,
    ) -> None:
        if client is None and persist_dir is None:
            raise ValueError("ChromaConnector requires either persist_dir or client")

        self._manifest = manifest
        self._persist_dir = persist_dir
        self._collection_name = collection_name
        self._embedding_function = (
            embedding_function if embedding_function is not None else HashingEmbeddingFunction()
        )
        self._client: chromadb.ClientAPI | None = client

    def _get_collection(self):
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self._persist_dir),
                settings=chromadb.config.Settings(anonymized_telemetry=False),
            )
        return self._client.get_or_create_collection(
            self._collection_name, embedding_function=self._embedding_function
        )

    def manifest(self) -> CapabilityManifest:
        return self._manifest

    async def retrieve(self, req: RetrievalRequest) -> RetrievalResult:
        collection = self._get_collection()
        count = collection.count()
        if count == 0:
            return RetrievalResult(evidence=[])

        n_results = min(req.top_k, count)
        results = collection.query(query_texts=[req.query], n_results=n_results)

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        evidence = [
            Evidence(
                source_id=self._manifest.connector_id,
                content=doc,
                # Chroma returns a distance (lower = more similar); invert
                # to a similarity-style score so higher = better, matching
                # the convention other connectors use for Evidence.score.
                score=1.0 / (1.0 + dist),
                uri=(meta or {}).get("source_path", doc_id),
                retrieved_at=datetime.now(timezone.utc),
            )
            for doc_id, doc, dist, meta in zip(ids, documents, distances, metadatas)
        ]
        return RetrievalResult(evidence=evidence)

    async def health(self) -> HealthStatus:
        try:
            collection = self._get_collection()
            count = collection.count()
        except Exception as exc:  # noqa: BLE001 - report, don't crash health checks
            return HealthStatus(state=HealthState.DOWN, detail=str(exc))

        if count == 0:
            return HealthStatus(
                state=HealthState.DEGRADED,
                detail="collection is empty; run ingest_corpus() first",
            )
        return HealthStatus(state=HealthState.OK)