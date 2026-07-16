"""
Tests for fusion/normalize.py — per-source min-max score normalization.
"""

from __future__ import annotations

from datetime import datetime, timezone

from capretrieve.contracts.result import Evidence
from capretrieve.fusion.normalize import normalize_scores


def _ev(source_id: str, score: float, uri: str | None = None) -> Evidence:
    return Evidence(
        source_id=source_id,
        content="content",
        score=score,
        uri=uri,
        retrieved_at=datetime.now(timezone.utc),
    )


def test_empty_list_returns_empty():
    assert normalize_scores([]) == []


def test_single_item_normalizes_to_one():
    result = normalize_scores([_ev("a", 0.37)])
    assert result[0].score == 1.0


def test_min_max_normalization_within_source():
    items = [_ev("a", 0.0), _ev("a", 5.0), _ev("a", 10.0)]
    result = normalize_scores(items)
    scores = sorted(r.score for r in result)
    assert scores == [0.0, 0.5, 1.0]


def test_equal_scores_within_source_all_normalize_to_one():
    items = [_ev("a", 3.0), _ev("a", 3.0)]
    result = normalize_scores(items)
    assert all(r.score == 1.0 for r in result)


def test_normalization_is_scoped_per_source():
    """Source 'a' has a wide raw range, source 'b' a narrow one — each
    should be normalized independently, not against the global min/max."""
    items = [
        _ev("a", 0.0),
        _ev("a", 100.0),
        _ev("b", 0.4),
        _ev("b", 0.6),
    ]
    result = normalize_scores(items)

    a_scores = sorted(r.score for r in result if r.source_id == "a")
    b_scores = sorted(r.score for r in result if r.source_id == "b")

    assert a_scores == [0.0, 1.0]
    assert b_scores == [0.0, 1.0]  # 0.4/0.6 normalized within their own group


def test_does_not_mutate_input():
    original = _ev("a", 5.0)
    normalize_scores([original])
    assert original.score == 5.0  # unchanged


def test_preserves_provenance_fields():
    item = _ev("chroma", 0.8, uri="fixtures/data/corpus/x.md")
    result = normalize_scores([item])
    assert result[0].source_id == "chroma"
    assert result[0].uri == "fixtures/data/corpus/x.md"
    assert result[0].content == "content"