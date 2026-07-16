"""
planner.py — orchestrates the full planning pipeline: hard filter → soft
score → selection, producing an ExecutionPlan.

Deliberately takes a list of CapabilityManifest, not a list of Connector
or a Registry. This is what keeps the architectural invariant "the
planner never imports connectors or registry" mechanically true rather
than just documented — plan() has no way to reach a connector even if
someone tried, because it never receives one. The caller (a future
graph/nodes/plan.py) is responsible for fetching manifests from the
registry and handing only the manifests to this function.
"""

from __future__ import annotations

from capretrieve.manifest.models import CapabilityManifest
from capretrieve.planner.constraints import apply_hard_constraints
from capretrieve.planner.models.decision import SelectionDecision
from capretrieve.planner.models.plan import ExecutionPlan
from capretrieve.planner.models.requirements import QueryRequirements
from capretrieve.planner.scoring import score_candidate
from capretrieve.planner.selection import select


def plan(
    manifests: list[CapabilityManifest], requirements: QueryRequirements
) -> ExecutionPlan:
    """
    Produce an ExecutionPlan for one query's requirements against a set
    of candidate connector manifests.

    Every manifest gets exactly one SelectionDecision: hard-excluded (with
    a reason) or admitted (with a soft score). select() then turns that
    into the final chosen set.
    """
    decisions: list[SelectionDecision] = []

    for manifest in manifests:
        exclusion = apply_hard_constraints(manifest, requirements)
        if exclusion is not None:
            decisions.append(
                SelectionDecision(
                    connector_id=manifest.connector_id,
                    admitted=False,
                    exclusion_reason=exclusion,
                )
            )
            continue

        score = score_candidate(manifest, requirements)
        decisions.append(
            SelectionDecision(
                connector_id=manifest.connector_id,
                admitted=True,
                score=score,
            )
        )

    return select(decisions)