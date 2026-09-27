"""
CapRetrieve itself, wrapped as an evaluation Router.

Routing only: analyze -> plan. No retrieval, fusion or synthesis, which is
the same scope as the baselines, so the comparison is like for like.

The LLM client is built by the same bootstrap helper the real app uses, and
the manifests come from the same config dir, so what's evaluated here is
what runs in production. No connectors are instantiated: plan() only needs
manifests, so no Chroma ingest and no Tavily key are required.
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable, Sequence
from typing import Any

from capretrieve.evaluation.records import RouteDecision, to_jsonable


class CapRetrieveRouter:
    name = "capretrieve"
    deterministic = False  # the analyzer is an LLM

    def __init__(
        self,
        analyze_fn: Callable[[str], Any],
        plan_fn: Callable[[list[Any], Any], Any],
        manifests: Sequence[Any],
        model: str | None,
    ) -> None:
        self._analyze = analyze_fn
        self._plan = plan_fn
        self._manifests = list(manifests)
        self.model = model

    async def route(self, query: str) -> RouteDecision:
        if inspect.iscoroutinefunction(self._analyze):
            requirements = await self._analyze(query)
        else:
            # analyze() is synchronous: run it in a thread so --concurrency
            # actually parallelises the LLM calls instead of serialising them.
            requirements = await asyncio.to_thread(self._analyze, query)

        plan = self._plan(self._manifests, requirements)
        decision = _plan_to_decision(plan)
        decision.requirements = to_jsonable(requirements)
        return decision


def _plan_to_decision(plan: Any) -> RouteDecision:
    return RouteDecision(
        selected=list(plan.selected_connector_ids),
        excluded={
            d.connector_id: d.exclusion_reason.constraint
            for d in plan.decisions
            if d.exclusion_reason is not None
        },
    )


def build_capretrieve_router() -> CapRetrieveRouter:
    from capretrieve.bootstrap import _make_llm_client
    from capretrieve.manifest.loader import load_manifest_dir
    from capretrieve.planner.analyzer import analyze
    from capretrieve.planner.planner import plan
    from capretrieve.settings import get_settings

    settings = get_settings()
    client = _make_llm_client(settings, settings.analyzer_model)
    manifests = list(load_manifest_dir(settings.config_dir).values())
    if not manifests:
        raise FileNotFoundError(f"no manifests in {settings.config_dir}")

    return CapRetrieveRouter(
        analyze_fn=lambda q: analyze(client, q),
        plan_fn=plan,
        manifests=manifests,
        model=settings.analyzer_model,
    )