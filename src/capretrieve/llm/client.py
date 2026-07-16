"""
OpenRouterClient — a thin wrapper around OpenRouter's OpenAI-compatible
chat completions endpoint.

Kept intentionally minimal: this project's LLM usage (the requirement
analyzer, and later the synthesis step) needs one thing — send messages,
get back text — not the full surface of a heavyweight SDK. Uses httpx
directly rather than the `openai` package to avoid pulling in a large
dependency for a single endpoint.

NOTE: this class makes real network calls and has not been exercised
against the live OpenRouter API in this environment (openrouter.ai isn't
reachable from the sandbox this project was built in). Structural
correctness (request shape, response parsing) is based on OpenRouter's
documented OpenAI-compatible API, not a live-verified call. Smoke-test
this with a real OPENROUTER_API_KEY before relying on it.
"""

from __future__ import annotations

import httpx

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT_S = 30.0


class OpenRouterClient:
    """Satisfies llm.structured.CompletesText — has a .complete() method
    taking a list of {"role", "content"} messages and returning the
    assistant's raw text response."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def complete(self, messages: list[dict], **kwargs) -> str:
        """
        Send a chat completion request and return the assistant's raw
        text content of the first choice. Raises httpx.HTTPStatusError on
        a non-2xx response.
        """
        response = httpx.post(
            f"{OPENROUTER_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model,
                "messages": messages,
                **kwargs,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]