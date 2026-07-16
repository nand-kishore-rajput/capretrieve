"""
Per-source score normalization.

Different connectors' scores live on different, incomparable scales: a
Chroma cosine-derived similarity, a keyword-hit count from Obsidian, and
Tavily's own relevance score are not the same unit. Normalizing per
source (rather than globally) means each source's own best-to-worst
ordering is preserved while making cross-source comparison meaningful
enough for the final ranked merge.

This module does not call an LLM and never will — see
tests/architecture/test_fusion_has_no_llm.py.
"""

from __future__ import annotations

from capretrieve.contracts.result import Evidence


def normalize_scores(evidence: list[Evidence]) -> list[Evidence]:
    """
    Min-max normalize each Evidence item's score to [0, 1], computed
    separately per source_id group.

    A source contributing only one piece of evidence gets that item
    normalized to 1.0 — there's nothing to rank it against within its own
    source, and giving it the maximum rather than an arbitrary fraction
    avoids penalizing a source purely for returning fewer results.

    Returns new Evidence instances; does not mutate the input.
    """
    if not evidence:
        return []

    by_source: dict[str, list[Evidence]] = {}
    for item in evidence:
        by_source.setdefault(item.source_id, []).append(item)

    normalized: list[Evidence] = []
    for group in by_source.values():
        scores = [item.score for item in group]
        lo, hi = min(scores), max(scores)
        spread = hi - lo

        for item in group:
            if spread == 0:
                new_score = 1.0
            else:
                new_score = (item.score - lo) / spread
            normalized.append(item.model_copy(update={"score": new_score}))

    return normalized