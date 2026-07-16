"""
Tests for settings.py — reading configuration from environment variables,
with sensible defaults and a clear failure for the one required secret.
"""

from __future__ import annotations

from pathlib import Path

from capretrieve.settings import get_settings


def test_defaults_resolve_relative_to_repo_root(monkeypatch):
    for var in [
        "CONFIG_DIR",
        "VAULT_DIR",
        "CORPUS_DIR",
        "CHROMA_PERSIST_DIR",
        "OPENROUTER_API_KEY",
        "WEB_SEARCH_API_KEY",
    ]:
        monkeypatch.delenv(var, raising=False)

    settings = get_settings()

    assert settings.config_dir.name == "connectors"
    assert settings.vault_dir.name == "vault"
    assert settings.corpus_dir.name == "corpus"
    assert settings.config_dir.exists()
    assert settings.vault_dir.exists()
    assert settings.corpus_dir.exists()


def test_env_vars_override_defaults(monkeypatch, tmp_path):
    custom_vault = tmp_path / "my_vault"
    monkeypatch.setenv("VAULT_DIR", str(custom_vault))

    settings = get_settings()
    assert settings.vault_dir == custom_vault


def test_analyzer_and_synthesis_model_defaults(monkeypatch):
    monkeypatch.delenv("ANALYZER_MODEL", raising=False)
    monkeypatch.delenv("SYNTHESIS_MODEL", raising=False)

    settings = get_settings()
    assert settings.analyzer_model == "anthropic/claude-sonnet-5"
    assert settings.synthesis_model == "anthropic/claude-sonnet-5"


def test_model_env_vars_override_defaults(monkeypatch):
    monkeypatch.setenv("ANALYZER_MODEL", "some/other-model")
    settings = get_settings()
    assert settings.analyzer_model == "some/other-model"


def test_openrouter_api_key_defaults_to_none(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings = get_settings()
    assert settings.openrouter_api_key is None


def test_openrouter_api_key_reads_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
    settings = get_settings()
    assert settings.openrouter_api_key == "sk-or-test-key"


def test_require_openrouter_api_key_raises_when_unset(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    settings = get_settings()
    try:
        settings.require_openrouter_api_key()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "OPENROUTER_API_KEY" in str(exc)


def test_require_openrouter_api_key_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test-key")
    settings = get_settings()
    assert settings.require_openrouter_api_key() == "sk-or-test-key"


def test_default_top_k_and_max_fused_items_have_int_defaults(monkeypatch):
    monkeypatch.delenv("DEFAULT_TOP_K", raising=False)
    monkeypatch.delenv("MAX_FUSED_ITEMS", raising=False)

    settings = get_settings()
    assert isinstance(settings.default_top_k, int)
    assert isinstance(settings.max_fused_items, int)
    assert settings.default_top_k > 0


def test_default_top_k_env_var_is_parsed_as_int(monkeypatch):
    monkeypatch.setenv("DEFAULT_TOP_K", "7")
    settings = get_settings()
    assert settings.default_top_k == 7


def test_get_settings_returns_fresh_instance_each_call(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-one")
    first = get_settings()
    monkeypatch.setenv("OPENROUTER_API_KEY", "key-two")
    second = get_settings()

    assert first.openrouter_api_key == "key-one"
    assert second.openrouter_api_key == "key-two"