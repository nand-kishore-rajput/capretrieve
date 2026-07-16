"""
ObsidianConnector — implements the Connector protocol over a local
Obsidian vault.

Wraps vault.py (loading + frontmatter/tag parsing) and traversal.py
(link-neighbourhood expansion), and presents ONE connector to the rest of
the system with paradigm=graph_traversal, even though internally it
supports two retrieval modes:
  - keyword/tag lookup (default — req.filters has no "seed_note")
  - link-neighbourhood expansion from a seed note
    (req.filters = {"seed_note": "...", "depth": 1})

Which mode fires is a filter on the request, not a separate connector —
the planner never needs to know this connector has two internal
strategies; it only ever sees one paradigm value in the manifest.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from capretrieve.connectors.obsidian.traversal import expand_neighbourhood
from capretrieve.connectors.obsidian.vault import Note, load_vault
from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.contracts.result import Evidence, RetrievalResult
from capretrieve.manifest.models import CapabilityManifest


class ObsidianConnector:
    """
    manifest is injected rather than loaded internally, so it's guaranteed
    identical to whatever registry/static.py loaded from
    configs/connectors/obsidian.yaml — registry.register() checks this
    equality and rejects drift between the YAML and the connector.
    """

    def __init__(self, manifest: CapabilityManifest, vault_dir: Path) -> None:
        self._manifest = manifest
        self._vault_dir = vault_dir
        self._notes: dict[str, Note] | None = None

    def _ensure_loaded(self) -> dict[str, Note]:
        if self._notes is None:
            self._notes = load_vault(self._vault_dir)
        return self._notes

    def manifest(self) -> CapabilityManifest:
        return self._manifest

    async def retrieve(self, req: RetrievalRequest) -> RetrievalResult:
        notes = self._ensure_loaded()
        filters = req.filters or {}
        seed_note = filters.get("seed_note")

        if seed_note:
            depth = int(filters.get("depth", 1))
            matched_notes = expand_neighbourhood(notes, seed_note, depth=depth)
            scored = [(note, 1.0) for note in matched_notes]
        else:
            scored = self._keyword_search(notes, req.query)

        evidence = [
            Evidence(
                source_id=self._manifest.connector_id,
                content=note.content,
                score=score,
                uri=note.path,
                retrieved_at=datetime.now(timezone.utc),
            )
            for note, score in scored[: req.top_k]
        ]
        return RetrievalResult(evidence=evidence)

    def _keyword_search(
        self, notes: dict[str, Note], query: str
    ) -> list[tuple[Note, float]]:
        """Naive keyword/tag relevance: count of query terms appearing in
        note content, title, or tags. Deliberately simple — this connector
        exists to prove the contract works end-to-end, not to be a good
        search engine. Swapping this for a real index later doesn't
        change the Connector interface."""
        terms = [t.lower() for t in query.split() if t]
        scored: list[tuple[Note, float]] = []

        for note in notes.values():
            haystack = " ".join(
                [
                    note.note_name.lower(),
                    note.content.lower(),
                    " ".join(note.tags).lower(),
                ]
            )
            hits = sum(haystack.count(term) for term in terms)
            if hits > 0:
                scored.append((note, float(hits)))

        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored

    async def health(self) -> HealthStatus:
        if not self._vault_dir.exists():
            return HealthStatus(
                state=HealthState.DOWN,
                detail=f"vault_dir {self._vault_dir} does not exist",
            )
        try:
            notes = self._ensure_loaded()
        except Exception as exc:  # noqa: BLE001 - report, don't crash health checks
            return HealthStatus(state=HealthState.DEGRADED, detail=str(exc))
        if not notes:
            return HealthStatus(
                state=HealthState.DEGRADED, detail="vault loaded but contains no notes"
            )
        return HealthStatus(state=HealthState.OK)