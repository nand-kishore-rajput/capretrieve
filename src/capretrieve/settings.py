"""
settings.py — all runtime configuration read from environment variables,
in one place.

Deliberately not a Pydantic BaseSettings subclass — this project's config
surface is small enough that a plain dataclass reading os.environ
directly is easier to follow and doesn't add a pydantic-settings
dependency for a handful of fields. python-dotenv is used only to load a
.env file if present (local dev convenience); actual values always come
from the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]

# Default model slugs are pinned, real OpenRouter model IDs. An earlier
# version of this default used OpenRouter's website-displayed "-latest"
# alias (e.g. "anthropic/claude-sonnet-latest") on the assumption it was
# a valid API model ID that would dodge future deprecation — live
# testing against the real API proved that wrong: OpenRouter's
# completions endpoint rejects "-latest" aliases outright ("not a valid
# model ID"). Those aliases appear to be a website-only routing
# convenience, not something the /chat/completions endpoint accepts.
# So: this WILL need updating again whenever anthropic/claude-sonnet-5
# itself is eventually deprecated — there's no current alias-based way
# around that. Check https://openrouter.ai/anthropic for the current
# model list if requests start failing with "not a valid model ID" or a
# 404 on this endpoint again.


@dataclass
class Settings:
    # --- LLM (OpenRouter) ---
    openrouter_api_key: str | None = field(
        default_factory=lambda: os.environ.get("OPENROUTER_API_KEY")
    )
    analyzer_model: str = field(
        default_factory=lambda: os.environ.get(
            "ANALYZER_MODEL", "anthropic/claude-sonnet-5"
        )
    )
    synthesis_model: str = field(
        default_factory=lambda: os.environ.get(
            "SYNTHESIS_MODEL", "anthropic/claude-sonnet-5"
        )
    )

    # --- Web search (Tavily) ---
    web_search_api_key: str | None = field(
        default_factory=lambda: os.environ.get("WEB_SEARCH_API_KEY")
    )

    # --- Data locations ---
    config_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("CONFIG_DIR", str(REPO_ROOT / "configs" / "connectors"))
        )
    )
    vault_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("VAULT_DIR", str(REPO_ROOT / "fixtures" / "data" / "vault"))
        )
    )
    corpus_dir: Path = field(
        default_factory=lambda: Path(
            os.environ.get("CORPUS_DIR", str(REPO_ROOT / "fixtures" / "data" / "corpus"))
        )
    )
    chroma_persist_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("CHROMA_PERSIST_DIR", ".chroma"))
    )

    # --- Query defaults ---
    default_top_k: int = field(
        default_factory=lambda: int(os.environ.get("DEFAULT_TOP_K", "5"))
    )
    max_fused_items: int = field(
        default_factory=lambda: int(os.environ.get("MAX_FUSED_ITEMS", "10"))
    )

    def require_openrouter_api_key(self) -> str:
        if not self.openrouter_api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Set it in your environment or "
                ".env file before starting the API."
            )
        return self.openrouter_api_key


def get_settings() -> Settings:
    """Constructs a fresh Settings from the current environment. Not
    cached — tests and scripts that mutate os.environ between calls (e.g.
    monkeypatch) should see the change reflected."""
    return Settings()