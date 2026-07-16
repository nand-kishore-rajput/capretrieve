"""
Tests for fusion/merge.py — the full fusion pipeline: dedup -> normalize
-> rank.
"""

from __future__ import annotations

from datetime import datetime, timezone

from capretrieve.contracts.result import Evidence
from capretrieve.fusion.merge import fuse


def _ev(source_id: str, score: float, uri: str) -> Evidence:
    return Evidence(
        source_id=source_id,
        content="content",
        score=score,
        uri=uri,
        retrieved_at=datetime.now(timezone.utc),
    )


def test_empty_input_returns_empty():
    assert fuse([]) == []


def test_result_is_sorted_descending_by_score():
    items = [
        _ev("chroma", 0.2, "c1"),
        _ev("chroma", 0.9, "c2"),
        _ev("obsidian", 0.5, "o1"),
    ]
    result = fuse(items)
    scores = [r.score for r in result]
    assert scores == sorted(scores, reverse=True)


def test_preserves_provenance_across_sources():
    items = [_ev("obsidian", 1.0, "o1"), _ev("chroma", 1.0, "c1")]
    result = fuse(items)
    assert {r.source_id for r in result} == {"obsidian", "chroma"}


def test_dedup_happens_before_ranking():
    dup_low = _ev("chroma", 0.2, "same")
    dup_high = _ev("chroma", 0.9, "same")
    other = _ev("obsidian", 0.5, "o1")
    result = fuse([dup_low, dup_high, other])
    # only one "same"-uri item should survive, at its higher raw score
    chroma_items = [r for r in result if r.source_id == "chroma"]
    assert len(chroma_items) == 1


def test_max_items_caps_result_length():
    items = [_ev("chroma", float(i), f"c{i}") for i in range(10)]
    result = fuse(items, max_items=3)
    assert len(result) == 3


def test_max_items_none_returns_everything():
    items = [_ev("chroma", float(i), f"c{i}") for i in range(10)]
    result = fuse(items, max_items=None)
    assert len(result) == 10


def test_max_items_keeps_highest_scoring_items():
    items = [_ev("chroma", float(i), f"c{i}") for i in range(10)]
    result = fuse(items, max_items=2)
    # top 2 by normalized score should be c9 (score 9, normalizes to 1.0)
    # and c8 (normalizes to ~0.89) since normalization is per-source
    uris = {r.uri for r in result}
    assert "c9" in uris