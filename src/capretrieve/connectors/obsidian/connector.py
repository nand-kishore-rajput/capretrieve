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

The seed_note filter value originates from QueryRequirements.seed_entity,
extracted by an LLM purely from the query's own text — it has no way to
know a vault's exact note-name casing or exact wording (e.g. "project
retrospective" vs. the actual note "Project Retrospective"). retrieve()
therefore resolves seed_note against actual note names case-insensitively,
falling back to a substring match, rather than requiring an exact key
match into the notes dict.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from capretrieve.connectors.obsidian.traversal import expand_neighbourhood
from capretrieve.connectors.obsidian.vault import Note, load_vault
from capretrieve.contracts.health import HealthState, HealthStatus
from capretrieve.contracts.request import RetrievalRequest
from capretrieve.contracts.result import Evidence, RetrievalResult
from capretrieve.manifest.models import CapabilityManifest

_WORD_RE = re.compile(r"\w+")

# Common English function words that appear in almost every note and
# almost every question; counting them makes long notes win by volume.
_STOPWORDS = frozenset(
    "a about an and are as at be been but by can did do does for from had has "
    "have how i in is it its me my of on or our say says so than that the "
    "their them then there these they this to was we were what when where "
    "which who why will with you your".split()
)


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall(text.lower())


def _resolve_seed_note(notes: dict[str, Note], seed: str) -> str | None:
    """
    Resolve a possibly-imprecise seed phrase to an actual note_name key.

    Tries, in order: exact match, case-insensitive exact match, then a
    substring match in either direction (handles "project retrospective"
    matching "Project Retrospective", or a seed with extra words like "my
    project retrospective" still finding "Project Retrospective"). Returns
    None if nothing plausible is found — the caller treats that as "no
    matching seed", same as an unresolvable seed always has.
    """
    if seed in notes:
        return seed

    seed_lower = seed.strip().lower()
    for note_name in notes:
        if note_name.lower() == seed_lower:
            return note_name

    candidates = [
        note_name
        for note_name in notes
        if note_name.lower() in seed_lower or seed_lower in note_name.lower()
    ]
    if not candidates:
        return None
    # Prefer the longest matching note_name — the most specific match
    # when multiple note names could be substrings of a loosely-phrased
    # seed (or vice versa).
    return max(candidates, key=len)


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
        self._loaded_mtime: float | None = None

    def _vault_mtime(self) -> float:
        """Newest modification time across the vault's notes and the vault
        directory itself (which changes when a note is added or deleted)."""
        mtimes = [self._vault_dir.stat().st_mtime]
        mtimes.extend(p.stat().st_mtime for p in self._vault_dir.rglob("*.md"))
        return max(mtimes)

    def _ensure_loaded(self) -> dict[str, Note]:
        """Load the vault, reloading whenever a note has changed since the
        last load. The manifest declares freshness=live, and the planner
        routes on that — so a cache that never refreshes would be a lie."""
        mtime = self._vault_mtime()
        if self._notes is None or mtime != self._loaded_mtime:
            self._notes = load_vault(self._vault_dir)
            self._loaded_mtime = mtime
        return self._notes

    def manifest(self) -> CapabilityManifest:
        return self._manifest

    async def retrieve(self, req: RetrievalRequest) -> RetrievalResult:
        notes = self._ensure_loaded()
        filters = req.filters or {}
        seed_note = filters.get("seed_note")

        if seed_note:
            depth = int(filters.get("depth", 1))
            resolved_seed = _resolve_seed_note(notes, seed_note)
            if resolved_seed is not None:
                matched_notes = expand_neighbourhood(notes, resolved_seed, depth=depth)
                scored = [(note, 1.0) for note in matched_notes]
            else:
                # No note is titled like the seed; notes that mention it
                # are the next best thing to an empty answer.
                scored = self._keyword_search(notes, seed_note)
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
        """Naive keyword/tag relevance: count of whole-word query-term
        occurrences in note content, title, or tags, ignoring stopwords.
        Deliberately simple — this connector exists to prove the contract
        works end-to-end, not to be a good search engine. Swapping this
        for a real index later doesn't change the Connector interface."""
        terms = set(_tokenize(query)) - _STOPWORDS
        scored: list[tuple[Note, float]] = []
        if not terms:
            return scored

        for note in notes.values():
            words = Counter(
                _tokenize(" ".join([note.note_name, note.content, " ".join(note.tags)]))
            )
            hits = sum(words[term] for term in terms)
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