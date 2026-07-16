"""
Tests for planner/analyzer.py — the requirement analyzer, tested with a
fake LLM client returning canned JSON. No real OpenRouter call is made
here; see llm/client.py's docstring for why a real call needs manual
smoke-testing with OPENROUTER_API_KEY.
"""

from __future__ import annotations

import json

from capretrieve.planner.analyzer import analyze, load_prompt_template
from capretrieve.planner.models.requirements import (
    Freshness,
    ParadigmHint,
    PrivacySensitivity,
    QueryRequirements,
)


class FakeLLMClient:
    """Returns a fixed response regardless of the conversation, and
    records what it was called with."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], **kwargs) -> str:
        self.calls.append(list(messages))
        return self.response


def test_analyze_parses_valid_response_into_query_requirements():
    canned = json.dumps(
        {
            "paradigm_hint": "graph_traversal",
            "relational": True,
            "needs_freshness": "any",
            "privacy_sensitivity": "none",
            "expects_personal_knowledge": True,
        }
    )
    client = FakeLLMClient(canned)

    result = analyze(client, "What other notes link to my project retrospective?")

    assert result == QueryRequirements(
        paradigm_hint=ParadigmHint.GRAPH_TRAVERSAL,
        relational=True,
        needs_freshness=Freshness.ANY,
        privacy_sensitivity=PrivacySensitivity.NONE,
        expects_personal_knowledge=True,
    )


def test_analyze_sends_the_query_text_in_the_prompt():
    canned = json.dumps(
        {
            "paradigm_hint": "unknown",
            "relational": False,
            "needs_freshness": "any",
            "privacy_sensitivity": "none",
            "expects_personal_knowledge": False,
        }
    )
    client = FakeLLMClient(canned)

    analyze(client, "a very distinctive query string xyzzy123")

    sent_content = client.calls[0][0]["content"]
    assert "a very distinctive query string xyzzy123" in sent_content


def test_analyze_handles_markdown_fenced_response():
    canned = "```json\n" + json.dumps(
        {
            "paradigm_hint": "dense_semantic",
            "relational": False,
            "needs_freshness": "any",
            "privacy_sensitivity": "none",
            "expects_personal_knowledge": False,
        }
    ) + "\n```"
    client = FakeLLMClient(canned)

    result = analyze(client, "some query")
    assert result.paradigm_hint == ParadigmHint.DENSE_SEMANTIC


def test_analyze_returns_defaults_for_partial_json():
    """QueryRequirements fields all have defaults, so a response missing
    some fields should still validate rather than error."""
    canned = json.dumps({"relational": True})
    client = FakeLLMClient(canned)

    result = analyze(client, "some query")
    assert result.relational is True
    assert result.paradigm_hint == ParadigmHint.UNKNOWN  # default


def test_prompt_template_contains_query_placeholder():
    template = load_prompt_template()
    assert "{query}" in template


def test_prompt_template_describes_all_requirement_fields():
    template = load_prompt_template()
    for field_name in QueryRequirements.model_fields:
        assert field_name in template, f"prompt template doesn't mention {field_name}"