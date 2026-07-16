"""
ExecutionPlan / PlanStep — the final output of planner.py: which
connectors to actually query, plus the full decision trail for every
candidate considered (admitted or not).

Imports only stdlib + decision.py (itself stdlib-only), per the pure-models
architecture invariant (see requirements.py for the full rationale).
"""

from __future__ import annotations

from pydantic import BaseModel

from capretrieve.planner.models.decision import SelectionDecision


class PlanStep(BaseModel):
    """One connector selected to actually be queried, in relevance order."""

    connector_id: str
    score: float


class ExecutionPlan(BaseModel):
    """
    The planner's final output for a query: the ordered set of connectors
    to fan out to (steps), plus the complete audit trail of how every
    candidate was evaluated (decisions) — including ones that were
    hard-excluded or scored too low to select.

    An empty `steps` list is a valid, meaningful plan: "no source can
    satisfy this under the given constraints" (see selection.py).
    """

    steps: list[PlanStep]
    decisions: list[SelectionDecision]

    @property
    def selected_connector_ids(self) -> list[str]:
        return [step.connector_id for step in self.steps]

    @property
    def is_empty(self) -> bool:
        return len(self.steps) == 0

    def decision_for(self, connector_id: str) -> SelectionDecision | None:
        """Look up the decision record for a specific connector_id, e.g.
        to check its exclusion reason in a test."""
        for decision in self.decisions:
            if decision.connector_id == connector_id:
                return decision
        return None