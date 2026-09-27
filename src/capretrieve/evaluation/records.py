"""
Log schema for the routing evaluation.

The runner appends one RunRecord per (scenario, router, run) to a JSONL file.
Records hold raw observations only. Correctness against scenarios.yaml is
computed later by compare.py, so changing the scoring rules never means
re-running the LLM calls.

Replay: for the capretrieve router, `requirements` holds the full analyzer
output. Ablation and threshold sweeps rebuild QueryRequirements from it and
re-run plan() offline, with no LLM calls.
"""

from __future__ import annotations

import dataclasses
import enum
import json
from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, Field

SCHEMA_VERSION = 1


class RouteDecision(BaseModel):
    """What a router returns for one query."""

    selected: list[str]
    # connector_id -> machine-checkable constraint (capretrieve only)
    excluded: dict[str, str] = Field(default_factory=dict)
    # ids an LLM router returned that don't exist (tool_description only)
    invalid: list[str] = Field(default_factory=list)
    # analyzer output as plain JSON (capretrieve only), the replay source
    requirements: dict[str, Any] | None = None
    # router-specific raw output: TF-IDF scores, LLM JSON, ...
    raw_output: str | None = None


class Router(Protocol):
    """Anything the runner can evaluate."""

    name: str
    deterministic: bool  # True => the runner calls it once per scenario
    model: str | None  # LLM model id, None for non-LLM routers

    async def route(self, query: str) -> RouteDecision: ...


class RunRecord(BaseModel):
    """One line in the JSONL log."""

    schema_version: int = SCHEMA_VERSION
    batch_id: str
    scenario_id: str
    router: str
    run_idx: int
    model: str | None
    selected: list[str] = Field(default_factory=list)
    excluded: dict[str, str] = Field(default_factory=dict)
    invalid: list[str] = Field(default_factory=list)
    requirements: dict[str, Any] | None = None
    raw_output: str | None = None
    # non-null => the run failed. compare.py counts it as a failure,
    # never as an empty plan.
    error: str | None = None
    # 1 = first try succeeded. >1 = rate-limited and retried.
    attempts: int = 1
    latency_ms: float
    timestamp: datetime


def to_jsonable(obj: Any) -> Any:
    """Pydantic model, dataclass, or plain object -> JSON-safe dict/list/scalar."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        obj = dataclasses.asdict(obj)

    def _default(o: Any) -> Any:
        if isinstance(o, enum.Enum):
            return o.value
        if isinstance(o, (set, frozenset)):
            return sorted(o)
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"not JSON-serialisable: {type(o).__name__}")

    return json.loads(json.dumps(obj, default=_default))