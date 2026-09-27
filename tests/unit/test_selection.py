"""
Tests for planner/selection.py — three-stage selection policy:
Stage 1: personal-knowledge force-include for private_local connectors.
Stage 2: freshness force-include for live connectors on recent/live queries.
Stage 3: relative threshold over remaining candidates.
"""

from __future__ import annotations

from capretrieve.manifest.models import (
    CapabilityManifest,
    Freshness,
    Paradigm,
    PrivacyTier,
)
from capretrieve.planner.models.decision import ExclusionReason, SelectionDecision
from capretrieve.planner.models.requirements import QueryRequirements
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


def _manifest(connector_id: str, private: bool = True) -> CapabilityManifest:
    return CapabilityManifest(
        connector_id=connector_id,
        paradigm=Paradigm.DENSE_SEMANTIC,
        freshness=Freshness.INDEX_TIME,
        privacy_tier=PrivacyTier.PRIVATE_LOCAL if private else PrivacyTier.PUBLIC_EXTERNAL,
        query_leaks_externally=not private,
        scope="test",
    )


# ── Stage 2: relative threshold (unchanged behaviour) ──────────────────

def test_empty_when_nothing_admitted():
    decisions = [_excluded("a"), _excluded("b")]
    plan = select(decisions)
    assert plan.is_empty
    assert plan.selected_connector_ids == []
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
    assert plan.steps[0].score >= plan.steps[1].score >= plan.steps[2].score


def test_excluded_decisions_never_appear_in_steps():
    decisions = [_admitted("a", 1.0), _excluded("b")]
    plan = select(decisions)
    assert "b" not in plan.selected_connector_ids
    assert plan.decision_for("b").admitted is False


def test_decision_for_returns_none_for_unknown_connector():
    decisions = [_admitted("a", 1.0)]
    plan = select(decisions)
    assert plan.decision_for("nonexistent") is None


# ── Stage 1: personal-knowledge force-include ──────────────────────────

def _personal_reqs() -> QueryRequirements:
    return QueryRequirements(expects_personal_knowledge=True)


def _non_personal_reqs() -> QueryRequirements:
    return QueryRequirements(expects_personal_knowledge=False)


def test_personal_knowledge_force_includes_private_local_below_threshold():
    """This is the exact bug that surfaced in live testing: obsidian scored
    0.5 against chroma's 1.5 (0.33 relative), below the 0.75 threshold,
    so it was excluded even though the user asked 'what do my notes say'.
    With the force-include policy it should always be selected."""
    decisions = [_admitted("chroma", 1.5), _admitted("obsidian", 0.5)]
    manifests = {
        "chroma": _manifest("chroma", private=True),
        "obsidian": _manifest("obsidian", private=True),
    }
    plan = select(decisions, requirements=_personal_reqs(), manifests=manifests)
    assert set(plan.selected_connector_ids) == {"chroma", "obsidian"}


def test_personal_knowledge_does_not_force_include_public_external():
    """A public/external connector should never be force-included on a
    personal-knowledge query — it would bypass the privacy intent."""
    decisions = [_admitted("chroma", 1.5), _admitted("web", 0.5)]
    manifests = {
        "chroma": _manifest("chroma", private=True),
        "web": _manifest("web", private=False),
    }
    plan = select(decisions, requirements=_personal_reqs(), manifests=manifests)
    assert "chroma" in plan.selected_connector_ids
    assert "web" not in plan.selected_connector_ids


def test_no_personal_knowledge_flag_uses_threshold_only():
    """Without expects_personal_knowledge, the policy should behave
    exactly as before — no force-include, just the threshold."""
    decisions = [_admitted("chroma", 1.5), _admitted("obsidian", 0.5)]
    manifests = {
        "chroma": _manifest("chroma", private=True),
        "obsidian": _manifest("obsidian", private=True),
    }
    plan = select(decisions, requirements=_non_personal_reqs(), manifests=manifests)
    # obsidian (0.5) is below 0.75 * 1.5 = 1.125 threshold → excluded
    assert plan.selected_connector_ids == ["chroma"]


def test_select_without_requirements_uses_threshold_only():
    """Backward compatibility: calling select() without requirements or
    manifests (as existing unit tests do) still uses the threshold."""
    decisions = [_admitted("a", 1.0), _admitted("b", 0.3)]
    plan = select(decisions)
    assert plan.selected_connector_ids == ["a"]


def test_personal_knowledge_force_include_still_excludes_hard_blocked():
    """Hard-excluded connectors (admitted=False) are never resurrected
    by the force-include policy — they never reach admitted[] at all."""
    decisions = [_admitted("chroma", 1.5), _excluded("obsidian")]
    manifests = {
        "chroma": _manifest("chroma", private=True),
        "obsidian": _manifest("obsidian", private=True),
    }
    plan = select(decisions, requirements=_personal_reqs(), manifests=manifests)
    assert "obsidian" not in plan.selected_connector_ids
    assert plan.decision_for("obsidian").admitted is False


def test_s5_baseline_unaffected_when_not_personal_knowledge():
    """S5: a pure semantic query without personal knowledge should still
    select only chroma, even with the new policy in place."""
    decisions = [_admitted("chroma", 1.5), _admitted("obsidian", 0.5)]
    manifests = {
        "chroma": _manifest("chroma", private=True),
        "obsidian": _manifest("obsidian", private=True),
    }
    plan = select(
        decisions,
        requirements=QueryRequirements(
            expects_personal_knowledge=False,
        ),
        manifests=manifests,
    )
    assert plan.selected_connector_ids == ["chroma"]


# ── Stage 2: freshness force-include ──────────────────────────────────────────

def _live_manifest(connector_id: str) -> CapabilityManifest:
    return CapabilityManifest(
        connector_id=connector_id,
        paradigm=Paradigm.KEYWORD,
        freshness=Freshness.LIVE,
        privacy_tier=PrivacyTier.PUBLIC_EXTERNAL,
        query_leaks_externally=True,
        scope="test",
    )


def _static_manifest(connector_id: str) -> CapabilityManifest:
    return CapabilityManifest(
        connector_id=connector_id,
        paradigm=Paradigm.DENSE_SEMANTIC,
        freshness=Freshness.INDEX_TIME,
        privacy_tier=PrivacyTier.PRIVATE_LOCAL,
        query_leaks_externally=False,
        scope="test",
    )


def _freshness_reqs(freshness: str) -> QueryRequirements:
    from capretrieve.planner.models.requirements import Freshness as RF
    return QueryRequirements(needs_freshness=RF(freshness))


def test_freshness_live_force_includes_live_connector_below_threshold():
    """This is the exact bug from live testing: web_search scored 0.3
    against chroma's 1.0 for a 'latest research' query, so it was not
    selected despite needs_freshness=recent. With the force-include
    policy, live connectors are always selected for freshness queries."""
    decisions = [_admitted("chroma", 1.0), _admitted("web_search", 0.3)]
    manifests = {
        "chroma": _static_manifest("chroma"),
        "web_search": _live_manifest("web_search"),
    }
    plan = select(
        decisions,
        requirements=_freshness_reqs("recent"),
        manifests=manifests,
    )
    assert "web_search" in plan.selected_connector_ids
    assert "chroma" in plan.selected_connector_ids


def test_freshness_live_requirement_also_force_includes():
    decisions = [_admitted("chroma", 1.0), _admitted("web_search", 0.3)]
    manifests = {
        "chroma": _static_manifest("chroma"),
        "web_search": _live_manifest("web_search"),
    }
    plan = select(
        decisions,
        requirements=_freshness_reqs("live"),
        manifests=manifests,
    )
    assert "web_search" in plan.selected_connector_ids


def test_freshness_any_does_not_force_include_live_connector():
    """When needs_freshness=any, no force-include fires — just threshold."""
    decisions = [_admitted("chroma", 1.0), _admitted("web_search", 0.3)]
    manifests = {
        "chroma": _static_manifest("chroma"),
        "web_search": _live_manifest("web_search"),
    }
    plan = select(
        decisions,
        requirements=_freshness_reqs("any"),
        manifests=manifests,
    )
    assert "web_search" not in plan.selected_connector_ids


def test_freshness_force_include_does_not_resurrect_hard_blocked():
    """A hard-blocked connector (admitted=False) is never resurrected
    by the freshness force-include, even if it's a live source."""
    decisions = [_admitted("chroma", 1.0), _excluded("web_search")]
    manifests = {
        "chroma": _static_manifest("chroma"),
        "web_search": _live_manifest("web_search"),
    }
    plan = select(
        decisions,
        requirements=_freshness_reqs("live"),
        manifests=manifests,
    )
    assert "web_search" not in plan.selected_connector_ids
    assert plan.decision_for("web_search").admitted is False


def test_both_force_includes_can_fire_simultaneously():
    """Personal knowledge + freshness can both apply at once: obsidian
    force-included (private_local + personal knowledge), web_search
    force-included (live + freshness), chroma selected by threshold."""
    from capretrieve.planner.models.requirements import Freshness as RF
    decisions = [
        _admitted("chroma", 1.0),
        _admitted("obsidian", 0.2),
        _admitted("web_search", 0.2),
    ]
    manifests = {
        "chroma": _static_manifest("chroma"),
        "obsidian": _manifest("obsidian", private=True),
        "web_search": _live_manifest("web_search"),
    }
    plan = select(
        decisions,
        requirements=QueryRequirements(
            expects_personal_knowledge=True,
            needs_freshness=RF.RECENT,
        ),
        manifests=manifests,
    )
    assert set(plan.selected_connector_ids) == {"chroma", "obsidian", "web_search"}