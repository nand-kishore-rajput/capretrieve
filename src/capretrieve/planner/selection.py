"""
Selection policy — turns scored, hard-filter-surviving candidates into the
final selected set: single source, multiple sources, or empty.

Policy: select every candidate whose score is within RELATIVE_THRESHOLD of
the top score. This is deliberately simple (per the streamlined Phase 3
scope) and declared rather than learned:
  - A single standout candidate (e.g. a pure semantic query where one
    connector's paradigm matches and nothing else is close) selects alone
    — this is what keeps S5 from over-selecting.
  - Several genuinely comparable candidates (e.g. two connectors that both
    just get the "expects personal knowledge + private_local" bonus and
    nothing else distinguishes them) select together — this is what makes
    S1 return both local connectors rather than an arbitrary single pick.

An empty admitted set (every candidate was hard-excluded) produces an
empty plan — "no source can satisfy this under the given constraints" is
a valid, meaningful answer, not a failure to paper over.
"""

from __future__ import annotations

from capretrieve.planner.models.decision import SelectionDecision
from capretrieve.planner.models.plan import ExecutionPlan, PlanStep

RELATIVE_THRESHOLD = 0.75
"""A candidate is selected if its score >= RELATIVE_THRESHOLD * top_score.
Declared and tunable — not learned. See scoring.py for the same honest
framing on its bonus constants."""


def select(decisions: list[SelectionDecision]) -> ExecutionPlan:
    """
    Build the final ExecutionPlan from a full list of SelectionDecisions
    (one per candidate connector, admitted or not).
    """
    admitted = [d for d in decisions if d.admitted]

    if not admitted:
        return ExecutionPlan(steps=[], decisions=decisions)

    top_score = max(d.score for d in admitted)

    if top_score <= 0:
        # Nothing meaningfully matched anything about this query. Rather
        # than arbitrarily picking a zero-relevance connector, select the
        # single closest-to-plausible option (still zero-informative, but
        # deterministic) — in practice this means no candidate got any
        # bonus, which currently should not happen for any live scenario;
        # kept explicit rather than silently falling through.
        steps = [PlanStep(connector_id=admitted[0].connector_id, score=admitted[0].score)]
        return ExecutionPlan(steps=steps, decisions=decisions)

    selected = [d for d in admitted if d.score >= RELATIVE_THRESHOLD * top_score]
    # Stable order: highest score first, ties broken by connector_id for
    # determinism (dict/set ordering elsewhere shouldn't leak into plans).
    selected.sort(key=lambda d: (-d.score, d.connector_id))

    steps = [PlanStep(connector_id=d.connector_id, score=d.score) for d in selected]
    return ExecutionPlan(steps=steps, decisions=decisions)