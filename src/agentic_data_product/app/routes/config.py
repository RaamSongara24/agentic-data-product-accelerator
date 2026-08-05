"""Runtime configuration profile API (narrow P1)."""

from __future__ import annotations

from fastapi import APIRouter

from agentic_data_product.config import get_settings
from agentic_data_product.domain.config_profile import RuntimeConfigProfile

router = APIRouter(tags=["config"])


@router.get("/config/profile", response_model=RuntimeConfigProfile)
async def get_config_profile() -> RuntimeConfigProfile:
    """Return the active non-secret runtime/config profile for the fixed graph."""
    settings = get_settings()
    return RuntimeConfigProfile(
        profile_name=f"{settings.app_env}-default",
        app_env=settings.app_env,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        llm_base_url=settings.llm_base_url,
        llm_timeout_seconds=settings.llm_timeout_seconds,
        mapping_schema_retry_cap=settings.mapping_schema_retry_cap,
        mapping_logic_retry_cap=settings.mapping_logic_retry_cap,
    )
