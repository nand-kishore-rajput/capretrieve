"""
planner/analyzer.py — the requirement analyzer: LLM call -> structured
QueryRequirements.

Architectural invariant: this module (and the prompt it loads) sees ONLY
the query text and the QueryRequirements schema — never a connector name,
never manifest data, never registry access. This is "the single most
important isolation in the system": if the analyzer ever gains visibility
into which connectors exist, it can start smuggling tool-picking back in
disguised as "requirement extraction." Enforced by
tests/architecture/test_analyzer_isolation.py, which checks the prompt
file's literal text for known connector_ids.
"""

from __future__ import annotations

from pathlib import Path

from capretrieve.llm.structured import CompletesText, get_structured_output
from capretrieve.planner.models.requirements import QueryRequirements

PROMPT_PATH = Path(__file__).parent / "prompts" / "requirement_extraction.md"


def load_prompt_template() -> str:
    return PROMPT_PATH.read_text()


def analyze(client: CompletesText, query: str) -> QueryRequirements:
    """
    Extract QueryRequirements from a raw query string via an LLM client.

    `client` is injected (same dependency-injection pattern used for the
    connectors) so this is fully testable with a fake client returning
    canned JSON, without a real OpenRouter call or API key. The real
    llm.client.OpenRouterClient satisfies the same CompletesText protocol
    for actual use.
    """
    template = load_prompt_template()
    prompt = template.replace("{query}", query)

    messages = [{"role": "user", "content": prompt}]
    return get_structured_output(client, messages, QueryRequirements)