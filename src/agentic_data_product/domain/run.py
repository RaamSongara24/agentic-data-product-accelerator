"""Workflow run domain types."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agentic_data_product.domain.artefacts import ArtefactRef, BusinessRequirementPayload
from agentic_data_product.domain.enums import RunStatus
from agentic_data_product.domain.review import PendingReview
from agentic_data_product.domain.user_context import UserContext


class WorkflowRun(BaseModel):
    """One design workflow execution (``run_id`` = LangGraph ``thread_id``)."""

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


class CreateRunApiRequest(BaseModel):
    """Production ``POST /runs`` body — starts the M3 requirements + mapping graph."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    created_by: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    business_requirement: BusinessRequirementPayload | None = None
    user_context: UserContext | None = None


class RunDetail(BaseModel):
    """Run plus optional pending-review / latest-artefact summary for APIs."""

    model_config = ConfigDict(extra="forbid")

    run: WorkflowRun
    pending_review: PendingReview | None = None
    latest_artefact: ArtefactRef | None = None
