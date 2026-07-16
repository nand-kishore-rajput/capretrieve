"""
Tests for planner/selection.py — turning scored decisions into a final
ExecutionPlan (single / multi / empty).
"""

from __future__ import annotations

from capretrieve.planner.models.decision import ExclusionReason, SelectionDecision
from capretrieve.planner.selection import RELATIVE_THRESHOLD, select


def _admitted(connector_id: str, score: float) -> SelectionDecision:
    return SelectionDecision(connector_id=connector_id, admitted=True, score=score)


def _excluded(connector_id: str) -> SelectionDecision:
    return SelectionDecision(
        connector_id=connector_id,
        admitted=False,
        exclusion_reason=ExclusionReason(
            connector_id=connector_id, constraint="test", detail="test"
        ),
    )


def test_empty_when_nothing_admitted():
    decisions = [_excluded("a"), _excluded("b")]
    plan = select(decisions)
    assert plan.is_empty
    assert plan.selected_connector_ids == []
    # decisions are preserved even when empty, for the trace
    assert len(plan.decisions) == 2


def test_single_admitted_candidate_is_selected():
    decisions = [_admitted("a", 1.0), _excluded("b")]
    plan = select(decisions)
    assert plan.selected_connector_ids == ["a"]


def test_clear_standout_excludes_lower_scorers():
    decisions = [_admitted("a", 1.5), _admitted("b", 0.5), _admitted("c", 0.0)]
    plan = select(decisions)
    assert plan.selected_connector_ids == ["a"]


def test_tied_candidates_both_selected():
    decisions = [_admitted("a", 0.5), _admitted("b", 0.5)]
    plan = select(decisions)
    assert set(plan.selected_connector_ids) == {"a", "b"}


def test_near_top_candidate_within_threshold_is_selected():
    decisions = [_admitted("a", 1.0), _admitted("b", RELATIVE_THRESHOLD + 0.01)]
    plan = select(decisions)
    assert set(plan.selected_connector_ids) == {"a", "b"}


def test_just_below_threshold_candidate_is_excluded():
    decisions = [_admitted("a", 1.0), _admitted("b", RELATIVE_THRESHOLD - 0.01)]
    plan = select(decisions)
    assert plan.selected_connector_ids == ["a"]


def test_all_zero_scores_selects_a_single_deterministic_candidate():
    decisions = [_admitted("a", 0.0), _admitted("b", 0.0)]
    plan = select(decisions)
    assert len(plan.selected_connector_ids) == 1


def test_selected_steps_ordered_by_score_descending():
    decisions = [_admitted("a", 1.0), _admitted("b", 1.0), _admitted("c", 0.9)]
    plan = select(decisions)
    # a and b tie at 1.0 (both within threshold of top=1.0); c at 0.9 is
    # also within RELATIVE_THRESHOLD (0.75) of 1.0, so all three qualify
    assert plan.steps[0].score >= plan.steps[1].score >= plan.steps[2].score


def test_excluded_decisions_never_appear_in_steps():
    decisions = [_admitted("a", 1.0), _excluded("b")]
    plan = select(decisions)
    assert "b" not in plan.selected_connector_ids
    # but the exclusion is still recorded in the full decision trail
    assert plan.decision_for("b").admitted is False


def test_decision_for_returns_none_for_unknown_connector():
    decisions = [_admitted("a", 1.0)]
    plan = select(decisions)
    assert plan.decision_for("nonexistent") is None