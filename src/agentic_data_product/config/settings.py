"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the API and infrastructure connections."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = Field(default="agentic-data-product")
    app_env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)

    database_url: str = Field(
        default="postgresql+asyncpg://adp:adp@localhost:5432/adp",
    )

    # LLM — secrets via env only; never placed in LangGraph state.
    llm_provider: Literal["deterministic", "openai_compatible"] = Field(
        default="deterministic",
        description="Requirements agent provider (deterministic default for CI/tests)",
    )
    llm_api_key: SecretStr | None = Field(default=None)
    llm_model: str = Field(default="gpt-4o-mini")
    llm_base_url: str = Field(default="https://api.openai.com/v1")
    llm_timeout_seconds: float = Field(default=60.0, gt=0)

    # Mapping judge retry caps (ARCHITECTURE §7.3)
    mapping_schema_retry_cap: int = Field(default=2, ge=0)
    mapping_logic_retry_cap: int = Field(default=2, ge=0)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
