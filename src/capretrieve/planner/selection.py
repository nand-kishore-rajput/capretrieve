"""
Selection policy — turns scored, hard-filter-surviving candidates into the
final selected set: single source, multiple sources, or empty.

Three-stage policy:

Stage 1 — PERSONAL KNOWLEDGE FORCE-INCLUDE:
  When expects_personal_knowledge=True, every admitted connector whose
  manifest has privacy_tier=private_local is force-included regardless of
  its relative score. Rationale: a user asking "what do my notes say
  about X" is explicitly asking for their own local data — withholding a
  local source because a different local source scored higher on paradigm
  fit is wrong.

Stage 2 — FRESHNESS FORCE-INCLUDE:
  When needs_freshness is RECENT or LIVE, every admitted connector whose
  manifest has freshness=live is force-included regardless of its relative
  score. Rationale: a query asking for "latest research" or "what's
  current" explicitly wants a live source — scoring alone will not
  reliably select it when a local source has a higher paradigm-match
  bonus. Mirrors the same structure as the privacy hard-block and the
  personal-knowledge force-include: a declared constraint over typed
  manifest fields, not a soft preference.

Stage 3 — RELATIVE_THRESHOLD:
  Select every remaining candidate whose score is within
  RELATIVE_THRESHOLD of the top score.
  - A single standout candidate selects alone — keeps S5 from
    over-selecting.
  - Several comparable candidates select together — makes S1 return both
    local connectors.

An empty admitted set produces an empty plan — "no source can satisfy
this under the given constraints" is a valid, meaningful answer.
"""

from __future__ import annotations

from capretrieve.manifest.models import Freshness as ManifestFreshness
from capretrieve.manifest.models import PrivacyTier
from capretrieve.planner.models.decision import SelectionDecision
from capretrieve.planner.models.plan import ExecutionPlan, PlanStep
from capretrieve.planner.models.requirements import Freshness as RequirementFreshness
from capretrieve.planner.models.requirements import QueryRequirements

RELATIVE_THRESHOLD = 0.75


def select(
    decisions: list[SelectionDecision],
    requirements: QueryRequirements | None = None,
    manifests: dict | None = None,
) -> ExecutionPlan:
    """
    Build the final ExecutionPlan from a full list of SelectionDecisions.

    requirements and manifests are optional for backward compatibility
    with tests that exercise the threshold logic in isolation, but should
    always be provided in real usage (planner.py always passes them).
    """
    admitted = [d for d in decisions if d.admitted]

    if not admitted:
        return ExecutionPlan(steps=[], decisions=decisions)

    top_score = max(d.score for d in admitted)

    if top_score <= 0:
        steps = [PlanStep(connector_id=admitted[0].connector_id, score=admitted[0].score)]
        return ExecutionPlan(steps=steps, decisions=decisions)

    force_included: set[str] = set()

    if requirements is not None and manifests:
        # Stage 1: personal knowledge — force-include private_local connectors.
        if requirements.expects_personal_knowledge:
            for d in admitted:
                manifest = manifests.get(d.connector_id)
                if manifest is not None and manifest.privacy_tier == PrivacyTier.PRIVATE_LOCAL:
                    force_included.add(d.connector_id)

        # Stage 2: freshness — force-include live connectors when the query
        # needs recent or live data.
        if requirements.needs_freshness in (
            RequirementFreshness.RECENT, RequirementFreshness.LIVE
        ):
            for d in admitted:
                manifest = manifests.get(d.connector_id)
                if manifest is not None and manifest.freshness == ManifestFreshness.LIVE:
                    force_included.add(d.connector_id)

    # Stage 3: relative threshold over remaining candidates.
    selected = [
        d for d in admitted
        if d.connector_id in force_included
        or d.score >= RELATIVE_THRESHOLD * top_score
    ]

    selected.sort(key=lambda d: (-d.score, d.connector_id))
    steps = [PlanStep(connector_id=d.connector_id, score=d.score) for d in selected]
    return ExecutionPlan(steps=steps, decisions=decisions)