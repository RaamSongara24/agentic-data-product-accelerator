"""Canonical domain models for Milestone M1.

These strongly-typed models are contracts between future agents and
platform layers, but M1 only persists and retrieves them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ArtefactType(StrEnum):
    BUSINESS_REQUIREMENT = "business_requirement"
    TECHNICAL_REQUIREMENT = "technical_requirement"
    SEMANTIC_MODEL = "semantic_model"
    DATA_MODEL = "data_model"
    PIPELINE_SPECIFICATION = "pipeline_specification"
    METRIC_DEFINITIONS = "metric_definitions"
    REVIEW_PACKAGE = "review_package"


NonEmptyStr = Annotated[str, Field(min_length=1)]


class BusinessRequirement(BaseModel):
    intent: NonEmptyStr
    objectives: list[NonEmptyStr] = Field(default_factory=list)
    constraints: list[NonEmptyStr] = Field(default_factory=list)
    success_criteria: list[NonEmptyStr] = Field(default_factory=list)


class TechnicalRequirement(BaseModel):
    expected_behavior: list[NonEmptyStr] = Field(default_factory=list)
    entities: list[NonEmptyStr] = Field(default_factory=list)
    transformations: list[NonEmptyStr] = Field(default_factory=list)
    governance_requirements: list[NonEmptyStr] = Field(default_factory=list)
    acceptance_criteria: list[NonEmptyStr] = Field(default_factory=list)


class SemanticModel(BaseModel):
    metrics: list[NonEmptyStr] = Field(default_factory=list)
    dimensions: list[NonEmptyStr] = Field(default_factory=list)
    hierarchies: list[NonEmptyStr] = Field(default_factory=list)
    relationships: list[NonEmptyStr] = Field(default_factory=list)
    business_definitions: dict[str, str] = Field(default_factory=dict)


class DataModel(BaseModel):
    datasets: list[NonEmptyStr] = Field(default_factory=list)
    entities: list[NonEmptyStr] = Field(default_factory=list)
    attributes: list[NonEmptyStr] = Field(default_factory=list)
    keys: list[NonEmptyStr] = Field(default_factory=list)
    relationships: list[NonEmptyStr] = Field(default_factory=list)
    governance_metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineSpecification(BaseModel):
    ingestion: list[NonEmptyStr] = Field(default_factory=list)
    transformations: list[NonEmptyStr] = Field(default_factory=list)
    orchestration: list[NonEmptyStr] = Field(default_factory=list)
    validation: list[NonEmptyStr] = Field(default_factory=list)
    lineage: list[NonEmptyStr] = Field(default_factory=list)
    operational_behavior: list[NonEmptyStr] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    name: NonEmptyStr
    calculation: NonEmptyStr
    aggregation_rule: NonEmptyStr
    filters: list[NonEmptyStr] = Field(default_factory=list)
    grain: NonEmptyStr
    business_logic: NonEmptyStr


class MetricDefinitions(BaseModel):
    definitions: list[MetricDefinition] = Field(default_factory=list)


class ReviewPackage(BaseModel):
    assumptions: list[NonEmptyStr] = Field(default_factory=list)
    traceability: list[NonEmptyStr] = Field(default_factory=list)
    validation_results: list[NonEmptyStr] = Field(default_factory=list)
    unresolved_questions: list[NonEmptyStr] = Field(default_factory=list)
    implementation_recommendations: list[NonEmptyStr] = Field(default_factory=list)


ArtefactPayload = (
    BusinessRequirement
    | TechnicalRequirement
    | SemanticModel
    | DataModel
    | PipelineSpecification
    | MetricDefinitions
    | ReviewPackage
)

ARTEFACT_PAYLOAD_MODELS: dict[ArtefactType, type[BaseModel]] = {
    ArtefactType.BUSINESS_REQUIREMENT: BusinessRequirement,
    ArtefactType.TECHNICAL_REQUIREMENT: TechnicalRequirement,
    ArtefactType.SEMANTIC_MODEL: SemanticModel,
    ArtefactType.DATA_MODEL: DataModel,
    ArtefactType.PIPELINE_SPECIFICATION: PipelineSpecification,
    ArtefactType.METRIC_DEFINITIONS: MetricDefinitions,
    ArtefactType.REVIEW_PACKAGE: ReviewPackage,
}


def validate_payload(artefact_type: ArtefactType, payload: dict[str, Any]) -> dict[str, Any]:
    model_cls = ARTEFACT_PAYLOAD_MODELS[artefact_type]
    model = model_cls.model_validate(payload)
    dumped = model.model_dump(mode="json")
    return {str(key): value for key, value in dumped.items()}


class CanonicalArtefact(BaseModel):
    """Persisted artefact envelope."""

    model_config = ConfigDict(use_enum_values=True)

    artefact_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    artefact_type: ArtefactType
    version: int = Field(default=1, ge=1)
    payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WorkflowRunStatus(StrEnum):
    CREATED = "created"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


class WorkflowRun(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    name: NonEmptyStr
    status: WorkflowRunStatus = WorkflowRunStatus.CREATED
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    event_type: NonEmptyStr
    actor: str = "system"
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LineageEdge(BaseModel):
    edge_id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    from_artefact_id: UUID
    to_artefact_id: UUID
    relation: NonEmptyStr = "derived_from"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
