"""Workflow run domain types."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agentic_data_product.domain.enums import RunStatus


class WorkflowRun(BaseModel):
    """One design workflow execution (``run_id`` aligns with future LangGraph thread_id)."""

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    status: RunStatus = RunStatus.CREATED
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateWorkflowRunRequest(BaseModel):
    """API/store input for creating a run."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    run_id: UUID | None = None
