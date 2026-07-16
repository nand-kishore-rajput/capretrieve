"""
Tests for fusion/dedup.py — exact (source_id, uri) dedup within a source,
never collapsing across different sources.
"""

from __future__ import annotations

from datetime import datetime, timezone

from capretrieve.contracts.result import Evidence
from capretrieve.fusion.dedup import dedup


def _ev(source_id: str, score: float, uri: str | None, content: str = "content") -> Evidence:
    return Evidence(
        source_id=source_id,
        content=content,
        score=score,
        uri=uri,
        retrieved_at=datetime.now(timezone.utc),
    )


def test_empty_list_returns_empty():
    assert dedup([]) == []


def test_no_duplicates_returns_all_items():
    items = [_ev("a", 1.0, "u1"), _ev("a", 1.0, "u2")]
    assert dedup(items) == items


def test_exact_duplicate_keeps_highest_score():
    low = _ev("a", 0.3, "same-uri")
    high = _ev("a", 0.9, "same-uri")
    result = dedup([low, high])
    assert len(result) == 1
    assert result[0].score == 0.9


def test_same_uri_different_source_not_deduped():
    """Same uri from two different connectors is NOT a duplicate — it's
    two independently-provenanced pieces of evidence."""
    a = _ev("obsidian", 0.5, "shared-uri")
    b = _ev("chroma", 0.7, "shared-uri")
    result = dedup([a, b])
    assert len(result) == 2
    assert {r.source_id for r in result} == {"obsidian", "chroma"}


def test_items_with_no_uri_are_never_deduped_against_each_other():
    a = _ev("web_search", 0.5, None, content="result A")
    b = _ev("web_search", 0.5, None, content="result B")
    result = dedup([a, b])
    assert len(result) == 2


def test_preserves_first_seen_order_for_surviving_items():
    a = _ev("a", 0.5, "u1")
    b = _ev("a", 0.5, "u2")
    c = _ev("a", 0.9, "u1")  # duplicate of a, higher score
    result = dedup([a, b, c])
    # first-seen order: u1 (now with c's higher score), then u2
    assert [r.uri for r in result] == ["u1", "u2"]
    assert result[0].score == 0.9