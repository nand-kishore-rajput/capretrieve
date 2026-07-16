"""
Tests for planner/constraints.py — the two hard rules: privacy leak and
paradigm fit.
"""

from __future__ import annotations

import pytest

from capretrieve.manifest.models import (
    CapabilityManifest,
    Freshness,
    Paradigm,
    PrivacyTier,
)
from capretrieve.planner.constraints import (
    PARADIGM_MISMATCH_CONSTRAINT,
    PRIVACY_LEAK_CONSTRAINT,
    apply_hard_constraints,
)
from capretrieve.planner.models.requirements import (
    ParadigmHint,
    PrivacySensitivity,
    QueryRequirements,
)


def _manifest(**overrides) -> CapabilityManifest:
    defaults = dict(
        connector_id="test_connector",
        paradigm=Paradigm.DENSE_SEMANTIC,
        freshness=Freshness.INDEX_TIME,
        privacy_tier=PrivacyTier.PRIVATE_LOCAL,
        query_leaks_externally=False,
        scope="test",
    )
    defaults.update(overrides)
    return CapabilityManifest(**defaults)


def _requirements(**overrides) -> QueryRequirements:
    return QueryRequirements(**overrides)


@pytest.mark.parametrize(
    "sensitivity", [PrivacySensitivity.PERSONAL, PrivacySensitivity.CONFIDENTIAL]
)
def test_privacy_leak_excludes_leaking_connector(sensitivity):
    manifest = _manifest(query_leaks_externally=True)
    reqs = _requirements(privacy_sensitivity=sensitivity)

    reason = apply_hard_constraints(manifest, reqs)

    assert reason is not None
    assert reason.constraint == PRIVACY_LEAK_CONSTRAINT
    assert reason.connector_id == "test_connector"


def test_privacy_leak_does_not_exclude_non_leaking_connector():
    manifest = _manifest(query_leaks_externally=False)
    reqs = _requirements(privacy_sensitivity=PrivacySensitivity.CONFIDENTIAL)

    assert apply_hard_constraints(manifest, reqs) is None


def test_privacy_none_does_not_exclude_even_a_leaking_connector():
    manifest = _manifest(query_leaks_externally=True)
    reqs = _requirements(privacy_sensitivity=PrivacySensitivity.NONE)

    assert apply_hard_constraints(manifest, reqs) is None


def test_paradigm_mismatch_excludes_non_graph_connector_for_relational_query():
    manifest = _manifest(paradigm=Paradigm.DENSE_SEMANTIC)
    reqs = _requirements(relational=True)

    reason = apply_hard_constraints(manifest, reqs)

    assert reason is not None
    assert reason.constraint == PARADIGM_MISMATCH_CONSTRAINT


def test_paradigm_mismatch_does_not_exclude_graph_connector_for_relational_query():
    manifest = _manifest(paradigm=Paradigm.GRAPH_TRAVERSAL)
    reqs = _requirements(relational=True)

    assert apply_hard_constraints(manifest, reqs) is None


def test_paradigm_check_does_not_apply_when_not_relational():
    manifest = _manifest(paradigm=Paradigm.DENSE_SEMANTIC)
    reqs = _requirements(relational=False)

    assert apply_hard_constraints(manifest, reqs) is None


def test_keyword_connector_excluded_for_relational_query():
    manifest = _manifest(paradigm=Paradigm.KEYWORD)
    reqs = _requirements(relational=True)

    reason = apply_hard_constraints(manifest, reqs)
    assert reason is not None
    assert reason.constraint == PARADIGM_MISMATCH_CONSTRAINT


def test_privacy_checked_before_paradigm_when_both_would_fire():
    """If a connector both leaks and mismatches paradigm, the reported
    reason should be deterministic (privacy first)."""
    manifest = _manifest(query_leaks_externally=True, paradigm=Paradigm.KEYWORD)
    reqs = _requirements(
        relational=True, privacy_sensitivity=PrivacySensitivity.CONFIDENTIAL
    )

    reason = apply_hard_constraints(manifest, reqs)
    assert reason.constraint == PRIVACY_LEAK_CONSTRAINT


def test_connector_surviving_both_checks_returns_none():
    manifest = _manifest(
        query_leaks_externally=False, paradigm=Paradigm.GRAPH_TRAVERSAL
    )
    reqs = _requirements(
        relational=True, privacy_sensitivity=PrivacySensitivity.CONFIDENTIAL
    )

    assert apply_hard_constraints(manifest, reqs) is None