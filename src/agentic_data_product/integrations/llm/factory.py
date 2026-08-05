"""Build an LLM client from application settings (no secrets in graph state)."""

from __future__ import annotations

from agentic_data_product.config.settings import Settings, get_settings
from agentic_data_product.integrations.llm.base import LlmClient
from agentic_data_product.integrations.llm.deterministic import DeterministicLlmClient
from agentic_data_product.integrations.llm.openai_compatible import OpenAICompatibleLlmClient


def create_llm_client(settings: Settings | None = None) -> LlmClient:
    """Return the configured LLM client.

    ``deterministic`` is the default so CI and golden tests need no API key.
    ``openai_compatible`` requires ``LLM_API_KEY`` in the environment.
    """
    cfg = settings or get_settings()
    if cfg.llm_provider == "deterministic":
        return DeterministicLlmClient()
    if cfg.llm_provider == "openai_compatible":
        if cfg.llm_api_key is None or not cfg.llm_api_key.get_secret_value():
            msg = "LLM_API_KEY is required when LLM_PROVIDER=openai_compatible"
            raise ValueError(msg)
        return OpenAICompatibleLlmClient(
            api_key=cfg.llm_api_key,
            model=cfg.llm_model,
            base_url=cfg.llm_base_url,
            timeout_seconds=cfg.llm_timeout_seconds,
        )
    msg = f"Unsupported LLM_PROVIDER: {cfg.llm_provider!r}"
    raise ValueError(msg)
