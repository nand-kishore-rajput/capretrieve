"""
Tests for llm/client.py — OpenRouterClient's request construction and
error handling, using a monkeypatched httpx.post rather than a real
network call to openrouter.ai.

Covers the two real issues this class hit during Phase 5 end-to-end
testing: a missing default max_tokens (Anthropic requires it) and a bare
httpx.HTTPStatusError that hid the actual response body on failure.
"""

from __future__ import annotations

import httpx
import pytest

from capretrieve.llm.client import (
    DEFAULT_MAX_TOKENS,
    EmptyCompletionError,
    LLMClient,
    LLMError,
)
OpenRouterError = LLMError
OpenRouterClient = LLMClient


class FakeResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._json_data = json_data
        self.text = text or (str(json_data) if json_data else "")

    def json(self) -> dict:
        return self._json_data


def _success_response(content: str = "hello from the model") -> FakeResponse:
    return FakeResponse(
        status_code=200,
        json_data={"choices": [{"message": {"content": content}}]},
    )


def test_complete_returns_message_content(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _success_response("the answer")

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="test-key", model="anthropic/claude-sonnet-latest")
    result = client.complete([{"role": "user", "content": "hi"}])

    assert result == "the answer"


def test_complete_sends_correct_url_and_auth_header(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        return _success_response()

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="my-secret-key", model="some/model")
    client.complete([{"role": "user", "content": "hi"}])

    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer my-secret-key"


def test_complete_includes_default_max_tokens(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return _success_response()

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="key", model="some/model")
    client.complete([{"role": "user", "content": "hi"}])

    assert captured["json"]["max_tokens"] == DEFAULT_MAX_TOKENS


def test_complete_allows_overriding_max_tokens_per_call(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return _success_response()

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="key", model="some/model")
    client.complete([{"role": "user", "content": "hi"}], max_tokens=100)

    assert captured["json"]["max_tokens"] == 100


def test_complete_constructor_max_tokens_override(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return _success_response()

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="key", model="some/model", max_tokens=2048)
    client.complete([{"role": "user", "content": "hi"}])

    assert captured["json"]["max_tokens"] == 2048


def test_complete_sends_model_and_messages(monkeypatch):
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["json"] = json
        return _success_response()

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="key", model="anthropic/claude-sonnet-latest")
    messages = [{"role": "user", "content": "distinctive query xyzzy"}]
    client.complete(messages)

    assert captured["json"]["model"] == "anthropic/claude-sonnet-latest"
    assert captured["json"]["messages"] == messages


def test_complete_raises_openrouter_error_with_body_on_400(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(
            status_code=400,
            text='{"error": {"message": "max_tokens is required", "code": 400}}',
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="key", model="some/model")

    with pytest.raises(OpenRouterError) as exc_info:
        client.complete([{"role": "user", "content": "hi"}])

    assert exc_info.value.status_code == 400
    assert "max_tokens is required" in exc_info.value.body
    # the body must be visible directly in the exception message, so a
    # traceback alone (no extra debugging) tells you what went wrong
    assert "max_tokens is required" in str(exc_info.value)


def test_complete_raises_openrouter_error_on_401(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(status_code=401, text='{"error": "Invalid API key"}')

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="bad-key", model="some/model")

    with pytest.raises(OpenRouterError) as exc_info:
        client.complete([{"role": "user", "content": "hi"}])

    assert exc_info.value.status_code == 401


def test_complete_does_not_raise_on_200(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return _success_response()

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="key", model="some/model")
    result = client.complete([{"role": "user", "content": "hi"}])
    assert result == "hello from the model"


def test_complete_raises_empty_completion_error_on_null_content(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(
            status_code=200,
            json_data={"choices": [{"message": {"content": None}, "finish_reason": "length"}]},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="key", model="some/model")
    with pytest.raises(EmptyCompletionError) as exc_info:
        client.complete([{"role": "user", "content": "hi"}])

    assert "length" in str(exc_info.value)
    assert "max_tokens" in str(exc_info.value).lower()


def test_complete_raises_empty_completion_error_on_missing_content_key(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(
            status_code=200,
            json_data={"choices": [{"message": {}, "finish_reason": "stop"}]},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="key", model="some/model")
    with pytest.raises(EmptyCompletionError):
        client.complete([{"role": "user", "content": "hi"}])


def test_complete_raises_empty_completion_error_on_empty_string_content(monkeypatch):
    def fake_post(url, headers, json, timeout):
        return FakeResponse(
            status_code=200,
            json_data={"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    client = LLMClient(api_base="https://openrouter.ai/api/v1", api_key="key", model="some/model")
    with pytest.raises(EmptyCompletionError):
        client.complete([{"role": "user", "content": "hi"}])


def test_empty_completion_error_includes_raw_response():
    raw = {"choices": [{"message": {"content": None}, "finish_reason": "length"}], "id": "gen-123"}
    error = EmptyCompletionError(raw)
    assert error.raw_response == raw
    assert "gen-123" in str(error)


def test_empty_completion_error_no_hint_for_non_length_finish_reason():
    raw = {"choices": [{"message": {"content": None}, "finish_reason": "stop"}]}
    error = EmptyCompletionError(raw)
    assert "reasoning" not in str(error).lower()