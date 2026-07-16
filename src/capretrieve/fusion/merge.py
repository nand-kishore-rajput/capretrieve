"""
fusion/merge.py — the single entry point that combines raw evidence from
every retrieved connector into one final, ranked, provenance-preserving
list.

Pipeline: dedup (within-source exact duplicates) -> normalize (per-source
score scaling) -> sort by normalized score descending. Every returned
Evidence item still carries its original source_id and uri — fusion
never collapses provenance, only ranks and trims.

This module does not call an LLM and never will — see
tests/architecture/test_fusion_has_no_llm.py. That's what keeps fusion
mechanically separate from generation/synthesize.py, which is the only
place an LLM call happens after retrieval.
"""

from __future__ import annotations

from capretrieve.contracts.result import Evidence
from capretrieve.fusion.dedup import dedup
from capretrieve.fusion.normalize import normalize_scores


def fuse(evidence: list[Evidence], max_items: int | None = None) -> list[Evidence]:
    """
    Combine raw evidence from potentially multiple connectors into one
    ranked list.

    max_items, if given, caps the number of items returned after ranking
    (e.g. to bound what gets handed to the synthesis prompt).
    """
    deduped = dedup(evidence)
    normalized = normalize_scores(deduped)
    normalized.sort(key=lambda item: item.score, reverse=True)

    if max_items is not None:
        normalized = normalized[:max_items]

    return normalized