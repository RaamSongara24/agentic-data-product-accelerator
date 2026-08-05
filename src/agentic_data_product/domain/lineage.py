"""Lineage edge domain types."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LineageEdge(BaseModel):
    """Directed edge from one artefact version to a downstream artefact version."""

    model_config = ConfigDict(extra="forbid")

    edge_id: UUID
    run_id: UUID
    from_artefact_id: UUID
    from_version: int = Field(ge=1)
    to_artefact_id: UUID
    to_version: int = Field(ge=1)
    relationship: str = Field(default="derived_from", min_length=1)
    created_at: datetime


class CreateLineageEdgeRequest(BaseModel):
    """API/store input for creating a lineage edge."""

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    from_artefact_id: UUID
    from_version: int = Field(ge=1)
    to_artefact_id: UUID
    to_version: int = Field(ge=1)
    relationship: str = Field(default="derived_from", min_length=1)
