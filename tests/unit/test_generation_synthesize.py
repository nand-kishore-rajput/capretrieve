"""
Tests for generation/synthesize.py — using a fake LLM client. No real
OpenRouter call is made; see synthesize.py's docstring for why a real
call needs manual smoke-testing.
"""

from __future__ import annotations

from datetime import datetime, timezone

from capretrieve.contracts.result import Evidence
from capretrieve.generation.synthesize import (
    NO_EVIDENCE_ANSWER,
    _format_evidence_block,
    load_prompt_template,
    synthesize,
)


class FakeLLMClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], **kwargs) -> str:
        self.calls.append(list(messages))
        return self.response


def _ev(source_id: str, content: str, uri: str | None = "https://example.com") -> Evidence:
    return Evidence(
        source_id=source_id,
        content=content,
        score=1.0,
        uri=uri,
        retrieved_at=datetime.now(timezone.utc),
    )


def test_synthesize_returns_the_client_response():
    client = FakeLLMClient("The answer is X [1].")
    result = synthesize(client, "some question", [_ev("chroma", "some evidence")])
    assert result == "The answer is X [1]."


def test_synthesize_includes_query_in_prompt():
    client = FakeLLMClient("answer")
    synthesize(client, "a very distinctive question xyzzy", [_ev("chroma", "some evidence")])
    sent = client.calls[0][0]["content"]
    assert "a very distinctive question xyzzy" in sent


def test_synthesize_includes_evidence_content_in_prompt():
    client = FakeLLMClient("answer")
    synthesize(client, "q", [_ev("chroma", "a very distinctive evidence snippet xyzzy")])
    sent = client.calls[0][0]["content"]
    assert "a very distinctive evidence snippet xyzzy" in sent


def test_format_evidence_block_includes_source_and_uri():
    block = _format_evidence_block([_ev("obsidian", "note content", uri="vault/note.md")])
    assert "source_id=obsidian" in block
    assert "uri=vault/note.md" in block
    assert "note content" in block


def test_format_evidence_block_handles_missing_uri():
    block = _format_evidence_block([_ev("web_search", "web content", uri=None)])
    assert "(no uri)" in block


def test_format_evidence_block_empty_list():
    assert _format_evidence_block([]) == "(no evidence was retrieved)"


def test_prompt_template_has_required_placeholders():
    template = load_prompt_template()
    assert "{query}" in template
    assert "{evidence_block}" in template

def test_synthesize_skips_llm_call_when_there_is_no_evidence():
    """No evidence means nothing to ground an answer in — and for a
    privacy-blocked query, calling the LLM would send the query out anyway."""
    client = FakeLLMClient("should not be used")

    answer = synthesize(client, "my private question", [])

    assert client.calls == []
    assert answer == NO_EVIDENCE_ANSWER
