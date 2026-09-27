"""
settings.py — all runtime configuration read from environment variables.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]

# Provider-agnostic defaults. Switch provider by changing LLM_API_BASE
# and LLM_API_KEY in .env — no code changes needed.
#
# OpenRouter:  LLM_API_BASE=https://openrouter.ai/api/v1
#              LLM_API_KEY=sk-or-...
#              ANALYZER_MODEL=anthropic/claude-sonnet-5
#
# Groq:        LLM_API_BASE=https://api.groq.com/openai/v1
#              LLM_API_KEY=gsk_...
#              ANALYZER_MODEL=llama-3.3-70b-versatile
#
# Free (OpenRouter free router):
#              LLM_API_BASE=https://openrouter.ai/api/v1
#              LLM_API_KEY=sk-or-...
#              ANALYZER_MODEL=openrouter/free


@dataclass
class Settings:
    # --- LLM provider ---
    llm_api_base: str = field(
        default_factory=lambda: os.environ.get(
            "LLM_API_BASE", "https://openrouter.ai/api/v1"
        )
    )
    llm_api_key: str | None = field(
        default_factory=lambda: os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")  # backward compat
    )
    analyzer_model: str = field(
        default_factory=lambda: os.environ.get(
            "ANALYZER_MODEL", "openrouter/free"
        )
    )
    synthesis_model: str = field(
        default_factory=lambda: os.environ.get(
            "SYNTHESIS_MODEL", "openrouter/free"
        )
    )
    llm_max_tokens: int = field(
        default_factory=lambda: int(os.environ.get("LLM_MAX_TOKENS", "4096"))
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

    def require_llm_api_key(self) -> str:
        if not self.llm_api_key:
            raise RuntimeError(
                "LLM_API_KEY (or OPENROUTER_API_KEY) is not set. "
                "Set it in your environment or .env file before starting the API."
            )
        return self.llm_api_key

    # Backward compat alias
    def require_openrouter_api_key(self) -> str:
        return self.require_llm_api_key()


def get_settings() -> Settings:
    return Settings()