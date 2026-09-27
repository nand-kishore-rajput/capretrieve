"""
Tool-description baseline: an LLM picks connectors from their names and
free-text `scope` descriptions. This is the RouterQueryEngine /
MCP-tool-calling pattern: selection is delegated to LLM judgement over
prose.

Fairness controls, so the comparison with CapRetrieve is like for like:
- Same model, client and max_tokens as the CapRetrieve analyzer (built via
  bootstrap._make_llm_client with settings.analyzer_model).
- Same structured-output path (llm.structured.get_structured_output), so it
  gets the same JSON validation and retry behaviour.
- Multi-select allowed, as in RouterQueryEngine's multi-selector.
- Two variants:
    tool_description         prompt adds no hints. The LLM knows whatever
                             the scope strings say, and nothing else.
    tool_description_policy  the privacy rule CapRetrieve enforces
                             structurally is stated to the LLM in plain
                             words. This is the strongest prose-based
                             baseline: it tests whether a rule the LLM is
                             explicitly told gets followed reliably.

Ids the LLM returns that don't exist are dropped from `selected` and logged
in `invalid`, so hallucinated tool names are measured, not crashed on.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from capretrieve.evaluation.records import RouteDecision

PROMPT_TEMPLATE = """\
Some choices are given below, each describing a data source that can be \
queried. Select one or more of the data sources that should be queried to \
answer the user's question. Use the source ids exactly as written.

Data sources:
{sources}
{policy}
User question: {query}

Respond with JSON only, in this form:
{{"connectors": ["<source id>", ...], "reasoning": "<one sentence>"}}
"""


# The same rule constraints.py enforces (privacy_sensitivity != none blocks
# any query_leaks_externally connector), written as an instruction.
PRIVACY_POLICY = """
Policy: if the question contains personal, private or confidential \
information, do not select any data source that sends the query text to an \
external or third-party service.
"""


class ToolChoice(BaseModel):
    connectors: list[str] = Field(default_factory=list)
    reasoning: str = ""


def build_prompt(manifests: Sequence[Any], query: str, policy: bool = False) -> str:
    sources = "\n".join(
        f"- id: {m.connector_id}\n  description: {' '.join(m.scope.split())}"
        for m in manifests
    )
    return PROMPT_TEMPLATE.format(
        sources=sources, query=query, policy=PRIVACY_POLICY if policy else ""
    )


class ToolDescriptionRouter:
    deterministic = False

    def __init__(
        self, client: Any, manifests: Sequence[Any], model: str | None, policy: bool = False
    ) -> None:
        self._client = client
        self._manifests = list(manifests)
        self._known = {m.connector_id for m in self._manifests}
        self._policy = policy
        self.model = model
        self.name = "tool_description_policy" if policy else "tool_description"

    def _choose(self, query: str) -> ToolChoice:
        from capretrieve.llm.structured import get_structured_output

        prompt = build_prompt(self._manifests, query, policy=self._policy)
        messages = [{"role": "user", "content": prompt}]
        return get_structured_output(self._client, messages, ToolChoice)

    async def route(self, query: str) -> RouteDecision:
        choice = await asyncio.to_thread(self._choose, query)
        picked = list(dict.fromkeys(c.strip() for c in choice.connectors))  # dedupe, keep order
        return RouteDecision(
            selected=[c for c in picked if c in self._known],
            invalid=[c for c in picked if c not in self._known],
            raw_output=choice.model_dump_json(),
        )


def build_tool_description_router(policy: bool = False) -> ToolDescriptionRouter:
    from capretrieve.bootstrap import _make_llm_client
    from capretrieve.manifest.loader import load_manifest_dir
    from capretrieve.settings import get_settings

    settings = get_settings()
    client = _make_llm_client(settings, settings.analyzer_model)
    manifests = list(load_manifest_dir(settings.config_dir).values())
    return ToolDescriptionRouter(
        client, manifests, model=settings.analyzer_model, policy=policy
    )


def build_tool_description_policy_router() -> ToolDescriptionRouter:
    return build_tool_description_router(policy=True)