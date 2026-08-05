"""Shared domain enumerations for artefacts, runs, and audit."""

from __future__ import annotations

from enum import StrEnum


class ArtefactType(StrEnum):
    """The seven canonical artefact kinds (ADR 002)."""

    BUSINESS_REQUIREMENT = "business_requirement"
    TECHNICAL_REQUIREMENT = "technical_requirement"
    SEMANTIC_MODEL = "semantic_model"
    DATA_MODEL = "data_model"
    PIPELINE_SPECIFICATION = "pipeline_specification"
    METRIC_DEFINITIONS = "metric_definitions"
    REVIEW_PACKAGE = "review_package"


class RunStatus(StrEnum):
    """Workflow run lifecycle states (HITL graph updates these from M2 onward)."""

    CREATED = "created"
    RUNNING = "running"
    WAITING_FOR_REVIEW = "waiting_for_review"
    APPROVED = "approved"
    TERMINATED = "terminated"
    FAILED = "failed"


class ReviewDecisionKind(StrEnum):
    """Human-in-the-loop review decisions (ADR 005)."""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVISIONS = "request_revisions"


class AuditAction(StrEnum):
    """Append-only audit event kinds written by the store."""

    RUN_CREATED = "run_created"
    RUN_STATUS_UPDATED = "run_status_updated"
    ARTEFACT_CREATED = "artefact_created"
    LINEAGE_CREATED = "lineage_created"
    REVIEW_SUBMITTED = "review_submitted"
