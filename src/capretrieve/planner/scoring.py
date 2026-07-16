"""
Soft scoring — a simple relevance ordering over connectors that survived
the hard filter (constraints.py).

Per the streamlined Phase 3 scope this is deliberately simple: a small,
declared, hand-set set of additive bonuses over typed manifest and
requirement fields — not a learned or heavily tuned weighting scheme.
"Declared and tunable, learning is future work" (matching the same
honest position the original phase plan takes for weights.yaml).

Architectural invariant: reads only typed fields from CapabilityManifest
and QueryRequirements, never manifest.scope. Never imports connectors/ or
registry/.
"""

from __future__ import annotations

from capretrieve.manifest.models import CapabilityManifest, Freshness as ManifestFreshness
from capretrieve.manifest.models import PrivacyTier
from capretrieve.planner.models.requirements import (
    Freshness as RequirementFreshness,
)
from capretrieve.planner.models.requirements import (
    ParadigmHint,
    QueryRequirements,
)

# Declared, hand-set bonuses. Kept as module-level constants rather than a
# config file for now — the streamlined Phase 3 scope doesn't call for a
# weights.yaml; if that's needed later it's a contained change here.
PARADIGM_MATCH_BONUS = 1.0
PERSONAL_KNOWLEDGE_LOCAL_BONUS = 0.5
FRESHNESS_MATCH_BONUS = 0.3

_PARADIGM_HINT_TO_MANIFEST = {
    ParadigmHint.DENSE_SEMANTIC: "dense_semantic",
    ParadigmHint.GRAPH_TRAVERSAL: "graph_traversal",
    ParadigmHint.KEYWORD: "keyword",
}


def score_candidate(
    manifest: CapabilityManifest, requirements: QueryRequirements
) -> float:
    """
    Compute a soft relevance score for one connector against one query's
    requirements. Only called for candidates that already survived the
    hard filter — this function doesn't re-check hard constraints.
    """
    score = 0.0

    expected_paradigm = _PARADIGM_HINT_TO_MANIFEST.get(requirements.paradigm_hint)
    if expected_paradigm is not None and manifest.paradigm.value == expected_paradigm:
        score += PARADIGM_MATCH_BONUS

    if requirements.expects_personal_knowledge and manifest.privacy_tier == PrivacyTier.PRIVATE_LOCAL:
        score += PERSONAL_KNOWLEDGE_LOCAL_BONUS

    if (
        requirements.needs_freshness != RequirementFreshness.ANY
        and manifest.freshness == ManifestFreshness.LIVE
    ):
        score += FRESHNESS_MATCH_BONUS

    return score