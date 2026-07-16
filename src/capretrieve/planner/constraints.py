"""
Hard constraint filter — boolean elimination over candidate connectors.

Per the streamlined Phase 3 scope, exactly two hard rules are kept (the
heavier latency/cost budget layer is deferred to Phase 6):

  1. Privacy leak: privacy_sensitivity != NONE eliminates any connector
     with query_leaks_externally = True. Drives S1.
  2. Paradigm fit: relational = True eliminates any connector whose
     paradigm != graph_traversal — a relational query structurally cannot
     be satisfied by keyword or dense-semantic retrieval. Drives S4.

Every elimination produces an ExclusionReason with a stable `constraint`
string and a human-readable `detail`, so the trace can say exactly why a
connector was blocked (S1's requirement).

Architectural invariant: this module reads only typed CapabilityManifest
and QueryRequirements fields. It never reads manifest.scope (enforced by
tests/architecture/test_no_freetext_in_planner.py) and never imports
connectors/ or registry/ (enforced by
tests/architecture/test_planner_imports.py).
"""

from __future__ import annotations

from capretrieve.manifest.models import CapabilityManifest, Paradigm
from capretrieve.planner.models.decision import ExclusionReason
from capretrieve.planner.models.requirements import (
    PrivacySensitivity,
    QueryRequirements,
)

PRIVACY_LEAK_CONSTRAINT = "privacy_leak"
PARADIGM_MISMATCH_CONSTRAINT = "paradigm_mismatch"


def check_privacy_leak(
    manifest: CapabilityManifest, requirements: QueryRequirements
) -> ExclusionReason | None:
    """privacy_sensitivity != NONE eliminates any connector that leaks the
    raw query text externally, regardless of how well it otherwise fits."""
    if requirements.privacy_sensitivity == PrivacySensitivity.NONE:
        return None
    if not manifest.query_leaks_externally:
        return None

    return ExclusionReason(
        connector_id=manifest.connector_id,
        constraint=PRIVACY_LEAK_CONSTRAINT,
        detail=(
            f"privacy_sensitivity={requirements.privacy_sensitivity.value} "
            f"and query_leaks_externally=true on {manifest.connector_id}"
        ),
    )


def check_paradigm_fit(
    manifest: CapabilityManifest, requirements: QueryRequirements
) -> ExclusionReason | None:
    """relational=True eliminates any connector that isn't graph_traversal
    — a relational/multi-hop query structurally cannot be satisfied by
    keyword or dense-semantic retrieval, no matter how well it otherwise
    scores."""
    if not requirements.relational:
        return None
    if manifest.paradigm == Paradigm.GRAPH_TRAVERSAL:
        return None

    return ExclusionReason(
        connector_id=manifest.connector_id,
        constraint=PARADIGM_MISMATCH_CONSTRAINT,
        detail=(
            f"paradigm={manifest.paradigm.value} cannot satisfy a "
            f"relational/graph-traversal query"
        ),
    )


HARD_CHECKS = (check_privacy_leak, check_paradigm_fit)


def apply_hard_constraints(
    manifest: CapabilityManifest, requirements: QueryRequirements
) -> ExclusionReason | None:
    """
    Run every hard check against one connector's manifest. Returns the
    first ExclusionReason encountered, or None if the connector survives
    every check.

    Checks run in a fixed order (privacy before paradigm) so that if a
    connector fails both, the reported reason is deterministic.
    """
    for check in HARD_CHECKS:
        reason = check(manifest, requirements)
        if reason is not None:
            return reason
    return None