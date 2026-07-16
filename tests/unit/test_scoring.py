"""
Tests for planner/scoring.py — the soft relevance score over candidates
that survived the hard filter.
"""

from __future__ import annotations

import pytest

from capretrieve.manifest.models import (
    CapabilityManifest,
    Freshness as ManifestFreshness,
    Paradigm,
    PrivacyTier,
)
from capretrieve.planner.models.requirements import (
    Freshness as RequirementFreshness,
)
from capretrieve.planner.models.requirements import (
    ParadigmHint,
    QueryRequirements,
)
from capretrieve.planner.scoring import (
    FRESHNESS_MATCH_BONUS,
    PARADIGM_MATCH_BONUS,
    PERSONAL_KNOWLEDGE_LOCAL_BONUS,
    score_candidate,
)


def _manifest(**overrides) -> CapabilityManifest:
    defaults = dict(
        connector_id="test_connector",
        paradigm=Paradigm.DENSE_SEMANTIC,
        freshness=ManifestFreshness.INDEX_TIME,
        privacy_tier=PrivacyTier.PRIVATE_LOCAL,
        query_leaks_externally=False,
        scope="test",
    )
    defaults.update(overrides)
    return CapabilityManifest(**defaults)


def test_no_bonuses_scores_zero():
    manifest = _manifest(paradigm=Paradigm.KEYWORD, privacy_tier=PrivacyTier.PUBLIC_EXTERNAL)
    reqs = QueryRequirements(
        paradigm_hint=ParadigmHint.DENSE_SEMANTIC,  # mismatches
        expects_personal_knowledge=False,
        needs_freshness=RequirementFreshness.ANY,
    )
    assert score_candidate(manifest, reqs) == 0.0


def test_paradigm_match_adds_bonus():
    manifest = _manifest(paradigm=Paradigm.DENSE_SEMANTIC)
    reqs = QueryRequirements(paradigm_hint=ParadigmHint.DENSE_SEMANTIC)
    assert score_candidate(manifest, reqs) == pytest.approx(PARADIGM_MATCH_BONUS)


def test_paradigm_mismatch_adds_no_bonus():
    manifest = _manifest(paradigm=Paradigm.GRAPH_TRAVERSAL)
    reqs = QueryRequirements(paradigm_hint=ParadigmHint.DENSE_SEMANTIC)
    assert score_candidate(manifest, reqs) == 0.0


def test_unknown_paradigm_hint_adds_no_bonus():
    manifest = _manifest(paradigm=Paradigm.DENSE_SEMANTIC)
    reqs = QueryRequirements(paradigm_hint=ParadigmHint.UNKNOWN)
    assert score_candidate(manifest, reqs) == 0.0


def test_personal_knowledge_bonus_requires_private_local():
    local_manifest = _manifest(privacy_tier=PrivacyTier.PRIVATE_LOCAL)
    public_manifest = _manifest(privacy_tier=PrivacyTier.PUBLIC_EXTERNAL)
    reqs = QueryRequirements(expects_personal_knowledge=True)

    assert score_candidate(local_manifest, reqs) == pytest.approx(
        PERSONAL_KNOWLEDGE_LOCAL_BONUS
    )
    assert score_candidate(public_manifest, reqs) == 0.0


def test_freshness_bonus_requires_live_manifest_and_non_any_requirement():
    live_manifest = _manifest(freshness=ManifestFreshness.LIVE)
    static_manifest = _manifest(freshness=ManifestFreshness.STATIC)

    reqs_recent = QueryRequirements(needs_freshness=RequirementFreshness.RECENT)
    reqs_any = QueryRequirements(needs_freshness=RequirementFreshness.ANY)

    assert score_candidate(live_manifest, reqs_recent) == pytest.approx(
        FRESHNESS_MATCH_BONUS
    )
    assert score_candidate(live_manifest, reqs_any) == 0.0
    assert score_candidate(static_manifest, reqs_recent) == 0.0


def test_bonuses_are_additive():
    manifest = _manifest(
        paradigm=Paradigm.GRAPH_TRAVERSAL,
        privacy_tier=PrivacyTier.PRIVATE_LOCAL,
        freshness=ManifestFreshness.LIVE,
    )
    reqs = QueryRequirements(
        paradigm_hint=ParadigmHint.GRAPH_TRAVERSAL,
        expects_personal_knowledge=True,
        needs_freshness=RequirementFreshness.LIVE,
    )

    expected = PARADIGM_MATCH_BONUS + PERSONAL_KNOWLEDGE_LOCAL_BONUS + FRESHNESS_MATCH_BONUS
    assert score_candidate(manifest, reqs) == pytest.approx(expected)