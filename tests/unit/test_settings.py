"""
Tests for settings.py — provider-agnostic LLM config, env var reading,
defaults, and the required-key guard.
"""

from __future__ import annotations

from capretrieve.settings import get_settings


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