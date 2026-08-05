"""HITL review decision contracts (ADR 005)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from agentic_data_product.domain.artefacts import ArtefactRef
from agentic_data_product.domain.enums import ReviewDecisionKind


class ReviewDecisionRequest(BaseModel):
    """API body for ``POST /runs/{id}/reviews``."""

    model_config = ConfigDict(extra="forbid")

    decision: ReviewDecisionKind
    comments: str = ""
    reviewer_id: str | None = None


class PendingReview(BaseModel):
    """Summary of the artefact currently waiting at a HITL interrupt."""

    model_config = ConfigDict(extra="forbid")

    artefact: ArtefactRef
    feedback: str | None = None
