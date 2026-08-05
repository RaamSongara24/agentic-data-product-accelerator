"""Unit tests for settings."""

import pytest

from agentic_data_product.config.settings import Settings, get_settings


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("API_PORT", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    get_settings.cache_clear()
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.app_name == "agentic-data-product"
    assert "postgresql+asyncpg://" in settings.database_url
    assert settings.api_port == 8000
    assert settings.llm_provider == "deterministic"
    assert settings.mapping_schema_retry_cap == 2


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "test-app")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("LOG_JSON", "true")
    monkeypatch.setenv("LLM_PROVIDER", "deterministic")
    monkeypatch.setenv("MAPPING_SCHEMA_RETRY_CAP", "3")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.app_name == "test-app"
    assert settings.api_port == 9000
    assert settings.log_json is True
    assert settings.mapping_schema_retry_cap == 3
