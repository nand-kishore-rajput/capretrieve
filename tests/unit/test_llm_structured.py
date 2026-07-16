"""
Tests for llm/structured.py — JSON parsing, Pydantic validation, and
retry-on-failure behavior, using a fake client rather than a real LLM.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from capretrieve.llm.structured import (
    StructuredOutputError,
    _extract_json,
    get_structured_output,
)


class SampleModel(BaseModel):
    name: str
    count: int


class ScriptedClient:
    """Returns each response in `responses` in order, one per call.
    Records every conversation it was called with."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls: list[list[dict]] = []

    def complete(self, messages: list[dict], **kwargs) -> str:
        self.calls.append(list(messages))
        return self._responses.pop(0)


def test_extract_json_passes_through_plain_json():
    assert _extract_json('{"a": 1}') == '{"a": 1}'


def test_extract_json_strips_markdown_fences():
    fenced = '```json\n{"a": 1}\n```'
    assert _extract_json(fenced) == '{"a": 1}'


def test_extract_json_strips_bare_fences_without_language_tag():
    fenced = '```\n{"a": 1}\n```'
    assert _extract_json(fenced) == '{"a": 1}'


def test_valid_json_on_first_attempt_returns_immediately():
    client = ScriptedClient(['{"name": "widget", "count": 3}'])
    result = get_structured_output(client, [{"role": "user", "content": "x"}], SampleModel)

    assert result == SampleModel(name="widget", count=3)
    assert len(client.calls) == 1


def test_invalid_json_retries_and_succeeds():
    client = ScriptedClient(
        [
            "not json at all",
            '{"name": "widget", "count": 3}',
        ]
    )
    result = get_structured_output(client, [{"role": "user", "content": "x"}], SampleModel)

    assert result == SampleModel(name="widget", count=3)
    assert len(client.calls) == 2


def test_valid_json_wrong_schema_retries_and_succeeds():
    client = ScriptedClient(
        [
            '{"wrong_field": "oops"}',
            '{"name": "widget", "count": 3}',
        ]
    )
    result = get_structured_output(client, [{"role": "user", "content": "x"}], SampleModel)
    assert result == SampleModel(name="widget", count=3)


def test_exhausting_retries_raises_structured_output_error():
    client = ScriptedClient(["nope", "still nope", "nope again"])

    with pytest.raises(StructuredOutputError) as exc_info:
        get_structured_output(
            client, [{"role": "user", "content": "x"}], SampleModel, max_retries=2
        )

    assert exc_info.value.model_name == "SampleModel"
    assert exc_info.value.attempts == 3


def test_retry_appends_corrective_message_to_conversation():
    client = ScriptedClient(["not json", '{"name": "widget", "count": 3}'])
    get_structured_output(client, [{"role": "user", "content": "x"}], SampleModel)

    # second call's conversation should include the bad response and a
    # corrective follow-up, not just the original message
    second_call_messages = client.calls[1]
    assert len(second_call_messages) > 1
    assert any(m["role"] == "assistant" for m in second_call_messages)


def test_json_with_extra_fenced_whitespace_still_parses():
    client = ScriptedClient(['  ```json\n  {"name": "widget", "count": 3}\n  ```  '])
    result = get_structured_output(client, [{"role": "user", "content": "x"}], SampleModel)
    assert result == SampleModel(name="widget", count=3)