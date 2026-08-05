"""Audit event domain types."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from agentic_data_product.domain.enums import AuditAction


class AuditEvent(BaseModel):
    """Append-only audit record for run and artefact mutations."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    run_id: UUID
    action: AuditAction
    entity_type: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    actor: str | None = None
