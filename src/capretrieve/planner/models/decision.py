"""
SelectionDecision / ExclusionReason — the audit trail of how a single
connector was evaluated during planning: admitted or hard-blocked, its
soft score if admitted, and a machine-checkable reason if not.

This is what makes "the exclusion is reported in the trace" (S1's
requirement) possible, and what tests/scenarios/test_scenarios.py checks
against fixtures/scenarios.yaml's must_exclude entries.

Imports only stdlib, per the pure-models architecture invariant (see
requirements.py for the full rationale).
"""

from __future__ import annotations

from pydantic import BaseModel


class ExclusionReason(BaseModel):
    """Why a candidate connector was eliminated by the hard filter."""

    connector_id: str

    constraint: str
    """Short, stable identifier for which hard rule fired — e.g.
    'privacy_leak' or 'paradigm_mismatch'. Stable strings so tests and
    fixtures/scenarios.yaml can check against them without parsing prose."""

    detail: str
    """Human-readable explanation for the trace / demo output."""


class SelectionDecision(BaseModel):
    """
    The full evaluation record for one connector: whether it survived the
    hard filter, its soft score if it did, and why not if it didn't.
    Exactly one of (score, exclusion_reason) is populated, matching
    `admitted`.
    """

    connector_id: str
    admitted: bool
    score: float | None = None
    exclusion_reason: ExclusionReason | None = None