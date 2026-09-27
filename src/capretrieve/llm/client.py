"""
llm/client.py — a thin, provider-agnostic OpenAI-compatible chat
completions client.

The API base URL, key, and model are all injected — nothing is
hardcoded to OpenRouter, Groq, or any other specific provider. Any
service that exposes an OpenAI-compatible /chat/completions endpoint
works as a drop-in by changing LLM_API_BASE and LLM_API_KEY in .env.

Tested providers:
  - OpenRouter: https://openrouter.ai/api/v1
  - Groq:       https://api.groq.com/openai/v1
  - Any other OpenAI-compatible endpoint

History of real bugs fixed here (so we don't re-learn them):
  1. Hardcoded model default went stale when anthropic/claude-3.5-sonnet
     was deprecated — now defaults live in settings.py and are env-var
     overridable.
  2. bare httpx.HTTPStatusError hid the response body on failure — now
     raises OpenRouterError with the full body included.
  3. Anthropic models (via OpenRouter) require max_tokens; added default.
  4. 200 OK with null content (reasoning tokens exhausted max_tokens) —
     now raises EmptyCompletionError with finish_reason hint.
"""

from __future__ import annotations

import httpx

DEFAULT_TIMEOUT_S = 30.0
DEFAULT_MAX_TOKENS = 4096


class LLMError(Exception):
    """Raised on a non-2xx response, with the actual response body
    included so the error is immediately actionable."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"LLM API error {status_code}: {body}")


# Keep the old name as an alias so existing code that catches
# OpenRouterError by name doesn't break.
OpenRouterError = LLMError


class EmptyCompletionError(Exception):
    """Raised when the API returns 200 OK but message content is
    null/missing/empty. Includes finish_reason and the full response
    so the cause is diagnosable without another round trip."""

    def __init__(self, raw_response: dict) -> None:
        self.raw_response = raw_response
        finish_reason = None
        choices = raw_response.get("choices") or []
        if choices:
            finish_reason = choices[0].get("finish_reason")

        hint = ""
        if finish_reason == "length":
            hint = (
                " finish_reason='length' suggests max_tokens was exhausted "
                "before any visible content was produced — try raising "
                "max_tokens or shortening the prompt."
            )

        super().__init__(
            f"LLM returned empty/null message content "
            f"(finish_reason={finish_reason!r}).{hint} "
            f"Full response: {raw_response}"
        )


class LLMClient:
    """
    Provider-agnostic OpenAI-compatible chat completions client.

    Satisfies llm.structured.CompletesText — has a .complete() method
    taking a list of {role, content} messages and returning the
    assistant's raw text response.

    api_base: full base URL, e.g.
        "https://openrouter.ai/api/v1"   (OpenRouter)
        "https://api.groq.com/openai/v1" (Groq)
    api_key: the provider's API key
    model:   the provider's model slug
    """

    def __init__(
        self,
        api_base: str,
        api_key: str,
        model: str,
        timeout: float = DEFAULT_TIMEOUT_S,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_tokens = max_tokens

    def complete(self, messages: list[dict], **kwargs) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            **kwargs,
        }

        response = httpx.post(
            f"{self._api_base}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout,
        )

        if response.status_code >= 400:
            raise LLMError(response.status_code, response.text)

        data = response.json()
        content = data["choices"][0]["message"].get("content")

        if not content:
            raise EmptyCompletionError(data)

        return content


# Keep old name as alias for backward compatibility
OpenRouterClient = LLMClient