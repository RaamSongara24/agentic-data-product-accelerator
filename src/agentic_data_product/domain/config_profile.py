"""Runtime configuration profile (narrow P1 — fixed graph, no workflow designer)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RuntimeConfigProfile(BaseModel):
    """Non-secret runtime settings operators can inspect (and demos can display).

    Secrets such as ``llm_api_key`` are never included.
    """

    model_config = ConfigDict(extra="forbid")

    profile_name: str = Field(description="Logical profile label for the fixed LangGraph")
    app_env: str
    llm_provider: Literal["deterministic", "openai_compatible"]
    llm_model: str
    llm_base_url: str
    llm_timeout_seconds: float
    mapping_schema_retry_cap: int
    mapping_logic_retry_cap: int
    graph: str = Field(
        default="hitl_seven_artefact",
        description="Fixed compiled graph identity (not a designer-selected workflow)",
    )
