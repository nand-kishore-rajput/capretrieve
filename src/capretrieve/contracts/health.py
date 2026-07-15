"""
HealthStatus — what a connector reports when asked if it's usable right now.

Used by graph/policies.py in Phase 6 to decide whether to re-plan around a
connector that's down or degraded. Kept minimal in Phase 1: just enough to
represent "fine" / "not fine, here's why".
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class HealthState(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"


class HealthStatus(BaseModel):
    state: HealthState
    detail: str | None = None