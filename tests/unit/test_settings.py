"""
Tests for settings.py — provider-agnostic LLM config, env var reading,
defaults, and the required-key guard.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import dotenv_values

from capretrieve.settings import Settings, get_settings


def test_defaults_resolve_relative_to_repo_root(monkeypatch):
    for var in ["CONFIG_DIR", "VAULT_DIR", "CORPUS_DIR", "CHROMA_PERSIST_DIR",
                "LLM_API_KEY", "OPENROUTER_API_KEY", "WEB_SEARCH_API_KEY"]:
        monkeypatch.delenv(var, raising=False)

    settings = get_settings()

    assert settings.config_dir.name == "connectors"
    assert settings.vault_dir.name == "vault"
    assert settings.corpus_dir.name == "corpus"
    assert settings.config_dir.exists()
    assert settings.vault_dir.exists()
    assert settings.corpus_dir.exists()


def test_llm_api_base_default_is_openrouter(monkeypatch):
    monkeypatch.delenv("LLM_API_BASE", raising=False)
    settings = get_settings()
    assert "openrouter" in settings.llm_api_base


def test_llm_api_base_env_var_overrides_default(monkeypatch):
    monkeypatch.setenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
    settings = get_settings()
    assert settings.llm_api_base == "https://api.groq.com/openai/v1"


def test_llm_api_key_reads_llm_api_key_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings = get_settings()
    assert settings.llm_api_key == "test-key"


def test_llm_api_key_falls_back_to_openrouter_api_key(monkeypatch):
    """Backward compat: OPENROUTER_API_KEY still works."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    settings = get_settings()
    assert settings.llm_api_key == "or-key"


def test_llm_api_key_prefers_llm_api_key_over_openrouter(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "new-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "old-key")
    settings = get_settings()
    assert settings.llm_api_key == "new-key"


def test_analyzer_and_synthesis_model_defaults(monkeypatch):
    monkeypatch.delenv("ANALYZER_MODEL", raising=False)
    monkeypatch.delenv("SYNTHESIS_MODEL", raising=False)
    settings = get_settings()
    assert settings.analyzer_model == "openrouter/free"
    assert settings.synthesis_model == "openrouter/free"


def test_model_env_vars_override_defaults(monkeypatch):
    monkeypatch.setenv("ANALYZER_MODEL", "llama-3.3-70b-versatile")
    settings = get_settings()
    assert settings.analyzer_model == "llama-3.3-70b-versatile"


def test_llm_api_key_defaults_to_none(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings = get_settings()
    assert settings.llm_api_key is None


def test_require_llm_api_key_raises_when_unset(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings = get_settings()
    try:
        settings.require_llm_api_key()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "LLM_API_KEY" in str(exc)


def test_require_openrouter_api_key_alias_still_works(monkeypatch):
    """Backward compat: the old method name still works."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    settings = get_settings()
    assert settings.require_openrouter_api_key() == "test-key"


def test_require_llm_api_key_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    settings = get_settings()
    assert settings.require_llm_api_key() == "sk-test"


def test_llm_max_tokens_default(monkeypatch):
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)
    settings = get_settings()
    assert settings.llm_max_tokens == 4096


def test_llm_max_tokens_env_var(monkeypatch):
    monkeypatch.setenv("LLM_MAX_TOKENS", "2000")
    settings = get_settings()
    assert settings.llm_max_tokens == 2000


def test_env_vars_override_defaults(monkeypatch, tmp_path):
    custom_vault = tmp_path / "my_vault"
    monkeypatch.setenv("VAULT_DIR", str(custom_vault))
    settings = get_settings()
    assert settings.vault_dir == custom_vault


def test_default_top_k_and_max_fused_items_have_int_defaults(monkeypatch):
    monkeypatch.delenv("DEFAULT_TOP_K", raising=False)
    monkeypatch.delenv("MAX_FUSED_ITEMS", raising=False)
    settings = get_settings()
    assert isinstance(settings.default_top_k, int)
    assert settings.default_top_k > 0


def test_get_settings_returns_fresh_instance_each_call(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "key-one")
    first = get_settings()
    monkeypatch.setenv("LLM_API_KEY", "key-two")
    second = get_settings()
    assert first.llm_api_key == "key-one"
    assert second.llm_api_key == "key-two"

def test_trace_view_token_reads_env(monkeypatch):
    monkeypatch.setenv("TRACE_VIEW_TOKEN", "s3cret")
    assert Settings().trace_view_token == "s3cret"


def test_trace_view_token_unset_or_empty_means_disabled(monkeypatch):
    monkeypatch.setenv("TRACE_VIEW_TOKEN", "")
    assert Settings().trace_view_token is None
    monkeypatch.delenv("TRACE_VIEW_TOKEN")
    assert Settings().trace_view_token is None


ENV_EXAMPLE = Path(__file__).parents[2] / ".env.example"

SETTINGS_ENV_VARS = [
    "LLM_API_BASE", "LLM_API_KEY", "OPENROUTER_API_KEY", "ANALYZER_MODEL",
    "SYNTHESIS_MODEL", "LLM_MAX_TOKENS", "WEB_SEARCH_API_KEY", "TRACE_VIEW_TOKEN",
    "CONFIG_DIR", "VAULT_DIR", "CORPUS_DIR", "CHROMA_PERSIST_DIR",
    "DEFAULT_TOP_K", "MAX_FUSED_ITEMS",
]


def _default_settings(monkeypatch) -> Settings:
    for var in SETTINGS_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    return Settings()


def test_empty_env_values_fall_back_to_defaults(monkeypatch):
    """`KEY=` in .env sets the variable to "", which must mean "use the
    default" — not int("") crashing, or Path("") pointing at the cwd."""
    defaults = _default_settings(monkeypatch)
    for var in SETTINGS_ENV_VARS:
        monkeypatch.setenv(var, "")

    assert Settings() == defaults


def test_env_example_copied_as_is_yields_defaults(monkeypatch):
    """The documented setup is `cp .env.example .env`; that must start."""
    defaults = _default_settings(monkeypatch)
    for key, value in dotenv_values(ENV_EXAMPLE).items():
        monkeypatch.setenv(key, value or "")

    assert Settings() == defaults


def test_env_example_ends_with_newline():
    """Otherwise `echo KEY=value >> .env` glues onto the last line."""
    assert ENV_EXAMPLE.read_text().endswith("\n")
