"""
Structured output helper: given anything with a .complete() method, a
prompt, and a Pydantic model, request JSON, parse it, validate it against
the model, and retry with a corrective follow-up message on failure.

Provider-agnostic on purpose — this doesn't know or care that the real
client is OpenRouterClient. Tests inject a fake client returning canned
text, so this module's logic (parsing, retry behavior) is fully tested
without any network access.
"""

from __future__ import annotations

import json
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)


class CompletesText(Protocol):
    def complete(self, messages: list[dict], **kwargs) -> str: ...


class StructuredOutputError(Exception):
    """Raised when the LLM's output couldn't be parsed/validated as the
    target model even after all retries."""

    def __init__(self, model_name: str, attempts: int, last_error: str) -> None:
        self.model_name = model_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"Failed to get valid {model_name} after {attempts} attempt(s): {last_error}"
        )


def _extract_json(text: str) -> str:
    """Strip markdown code fences if the model wrapped its JSON in them,
    despite being asked not to. Defensive, not load-bearing."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def get_structured_output(
    client: CompletesText,
    messages: list[dict],
    model: type[ModelT],
    max_retries: int = 2,
) -> ModelT:
    """
    Call client.complete() and parse/validate the response as `model`.

    On parse or validation failure, appends the bad response plus a
    corrective instruction to the conversation and retries, up to
    max_retries additional attempts. Raises StructuredOutputError if every
    attempt fails.
    """
    conversation = list(messages)
    last_error = ""

    for _ in range(max_retries + 1):
        raw = client.complete(conversation)
        cleaned = _extract_json(raw)

        try:
            data = json.loads(cleaned)
            return model.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = str(exc)
            conversation.append({"role": "assistant", "content": raw})
            conversation.append(
                {
                    "role": "user",
                    "content": (
                        "That response was not valid JSON matching the "
                        f"required schema. Error: {last_error}\n\n"
                        "Respond again with ONLY a valid JSON object "
                        "matching the schema, no other text."
                    ),
                }
            )

    raise StructuredOutputError(model.__name__, max_retries + 1, last_error)