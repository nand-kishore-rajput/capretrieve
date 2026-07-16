"""
OpenRouterClient — a thin wrapper around OpenRouter's OpenAI-compatible
chat completions endpoint.

Kept intentionally minimal: this project's LLM usage (the requirement
analyzer, and later the synthesis step) needs one thing — send messages,
get back text — not the full surface of a heavyweight SDK. Uses httpx
directly rather than the `openai` package to avoid pulling in a large
dependency for a single endpoint.

NOTE: this class makes real network calls. First live-tested against the
real OpenRouter API during Phase 5 end-to-end testing, which surfaced
three real issues fixed here:
  1. A hardcoded model default that had since been deprecated upstream
     (see settings.py).
  2. Requests failing with a bare "400 Bad Request" and no visible reason,
     because httpx's raise_for_status() doesn't include the response
     body. Anthropic's own API requires max_tokens as a mandatory field
     (unlike OpenAI's, where it's optional) and OpenRouter proxies that
     requirement through for Anthropic-backed models — this class now
     sends a default max_tokens, and more importantly, surfaces the
     actual response body in raised errors so future failures don't
     require another blind round trip to diagnose.
  3. A 200 OK response whose message content was null. This propagated
     silently as None through get_structured_output/synthesize all the
     way to trace building, which crashed on an unrelated-looking pydantic
     validation error far from the actual cause. The likely culprit:
     "adaptive thinking" / reasoning-capable models (e.g. Claude Sonnet 5)
     can consume the entire max_tokens budget on reasoning tokens before
     producing any visible content, especially with a low max_tokens like
     this client's default. This class now raises immediately, with the
     full response body, the moment content comes back null/missing,
     rather than letting None drift downstream.
"""

from __future__ import annotations

import httpx

OPENROUTER_API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT_S = 30.0
DEFAULT_MAX_TOKENS = 3000


class OpenRouterError(Exception):
    """Raised on a non-2xx response, with the actual response body
    included — unlike a bare httpx.HTTPStatusError, this is meant to be
    immediately actionable from the exception message alone."""

    def __init__(self, status_code: int, body: str) -> None:
        self.status_code = status_code
        self.body = body
        super().__init__(f"OpenRouter API error {status_code}: {body}")


class EmptyCompletionError(Exception):
    """Raised when OpenRouter returns 200 OK but the message content is
    null/missing/empty. Includes the raw response body and finish_reason
    (if present) so the likely cause — e.g. reasoning tokens exhausting
    max_tokens before any visible output — is diagnosable immediately
    rather than manifesting as a confusing failure somewhere downstream."""

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
                "before any visible content was produced — this is common "
                "with reasoning/'adaptive thinking' models that spend part "
                "of the token budget on internal reasoning. Try raising "
                "max_tokens."
            )

        super().__init__(
            f"OpenRouter returned an empty/null message content "
            f"(finish_reason={finish_reason!r}).{hint} Full response: {raw_response}"
        )


class OpenRouterClient:
    """Satisfies llm.structured.CompletesText — has a .complete() method
    taking a list of {"role", "content"} messages and returning the
    assistant's raw text response."""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = DEFAULT_TIMEOUT_S,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._max_tokens = max_tokens

    def complete(self, messages: list[dict], **kwargs) -> str:
        """
        Send a chat completion request and return the assistant's raw
        text content of the first choice.

        Raises OpenRouterError (with the response body included) on a
        non-2xx response, or EmptyCompletionError if the response is 200
        OK but content is null/missing/empty.

        max_tokens defaults to self._max_tokens but can be overridden per
        call via kwargs.
        """
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            **kwargs,
        }

        response = httpx.post(
            f"{OPENROUTER_API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout,
        )

        if response.status_code >= 400:
            raise OpenRouterError(response.status_code, response.text)

        data = response.json()
        content = data["choices"][0]["message"].get("content")

        if not content:
            raise EmptyCompletionError(data)

        return content