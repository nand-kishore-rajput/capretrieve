"""
Dedup evidence.

Deliberately scoped to exact (source_id, uri) matches — if the same
connector somehow returns the same underlying item twice (a retry, an
overlapping query), keep only the highest-scoring instance. This does
NOT merge evidence across different sources even if their content looks
similar: two connectors independently surfacing related content are
still two separate, independently-provenanced pieces of evidence, and
collapsing them would throw away exactly the provenance information
fusion/merge.py is supposed to preserve.

This module does not call an LLM and never will — see
tests/architecture/test_fusion_has_no_llm.py.
"""

from __future__ import annotations

from capretrieve.contracts.result import Evidence


def dedup(evidence: list[Evidence]) -> list[Evidence]:
    """
    Remove exact (source_id, uri) duplicates, keeping the highest-scoring
    instance of each. Items with uri=None are never considered duplicates
    of each other (there's no stable identity to dedup on), so they all
    pass through unchanged.

    Preserves the relative order of first occurrence for the surviving
    items.
    """
    best_by_key: dict[tuple[str, str], Evidence] = {}
    for item in evidence:
        if item.uri is None:
            continue
        key = (item.source_id, item.uri)
        if key not in best_by_key or item.score > best_by_key[key].score:
            best_by_key[key] = item

    seen_keys: set[tuple[str, str]] = set()
    result: list[Evidence] = []
    for item in evidence:
        if item.uri is None:
            result.append(item)
            continue
        key = (item.source_id, item.uri)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        result.append(best_by_key[key])

    return result