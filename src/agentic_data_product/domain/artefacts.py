"""Canonical artefact payload models and versioned envelope types."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentic_data_product.domain.enums import ArtefactType


class GovernanceMetadata(BaseModel):
    """Optional governance annotations propagated from source platforms."""

    model_config = ConfigDict(extra="forbid")

    sensitivity_labels: list[str] = Field(default_factory=list)
    classifications: list[str] = Field(default_factory=list)
    access_notes: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class SourceRef(BaseModel):
    """Reference to an upstream source object or document."""

    model_config = ConfigDict(extra="forbid")

    system: str = Field(min_length=1, description="Source system identifier")
    object_id: str = Field(min_length=1, description="Object or path identifier")
    display_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtefactRef(BaseModel):
    """Lightweight pointer to a specific artefact version."""

    model_config = ConfigDict(extra="forbid")

    artefact_id: UUID
    artefact_type: ArtefactType
    version: int = Field(ge=1)
    run_id: UUID


# --- Payload models (initial field sets for M1) ---


class BusinessRequirementPayload(BaseModel):
    """Intake artefact: business intent, objectives, constraints, success criteria."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    intent: str = Field(min_length=1)
    objectives: list[str] = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    stakeholders: list[str] = Field(default_factory=list)
    notes: str | None = None


class TechnicalRequirementPayload(BaseModel):
    """Refined functional/technical specification derived from the business requirement."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    behaviours: list[str] = Field(min_length=1)
    entities: list[str] = Field(default_factory=list)
    transformations: list[str] = Field(default_factory=list)
    governance_requirements: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    candidate_facts: list[str] = Field(default_factory=list)
    candidate_dimensions: list[str] = Field(default_factory=list)
    candidate_measures: list[str] = Field(default_factory=list)


class SemanticMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    grain: str | None = None


class SemanticDimension(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    hierarchy: list[str] = Field(default_factory=list)


class SemanticRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_entity: str = Field(min_length=1)
    to_entity: str = Field(min_length=1)
    cardinality: str = Field(min_length=1)
    description: str | None = None


class SemanticModelPayload(BaseModel):
    """Business-facing metrics, dimensions, hierarchies, and relationships."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    metrics: list[SemanticMetric] = Field(default_factory=list)
    dimensions: list[SemanticDimension] = Field(default_factory=list)
    relationships: list[SemanticRelationship] = Field(default_factory=list)
    business_definitions: dict[str, str] = Field(default_factory=dict)


class DataAttribute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    nullable: bool = True
    description: str | None = None
    governance_metadata: GovernanceMetadata | None = None


class DataEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str | None = None
    attributes: list[DataAttribute] = Field(default_factory=list)
    primary_key: list[str] = Field(default_factory=list)


class DataRelationship(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_entity: str = Field(min_length=1)
    to_entity: str = Field(min_length=1)
    from_keys: list[str] = Field(min_length=1)
    to_keys: list[str] = Field(min_length=1)
    cardinality: str = Field(min_length=1)


class DataModelPayload(BaseModel):
    """Logical datasets, entities, keys, and relationships."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    entities: list[DataEntity] = Field(min_length=1)
    relationships: list[DataRelationship] = Field(default_factory=list)
    mapping_context: dict[str, Any] = Field(default_factory=dict)
    governance_metadata: GovernanceMetadata | None = None


class PipelineStage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    kind: Literal["ingest", "transform", "validate", "publish", "other"] = "transform"
    description: str = Field(min_length=1)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)


class PipelineSpecificationPayload(BaseModel):
    """Declarative, technology-agnostic pipeline behaviour."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    stages: list[PipelineStage] = Field(min_length=1)
    orchestration_notes: str | None = None
    validation_rules: list[str] = Field(default_factory=list)
    operational_behaviour: dict[str, Any] = Field(default_factory=dict)
    lineage_notes: list[str] = Field(default_factory=list)


class MetricDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    calculation: str = Field(min_length=1)
    aggregation: str = Field(min_length=1)
    filters: list[str] = Field(default_factory=list)
    grain: str = Field(min_length=1)
    business_logic: str | None = None


class MetricDefinitionsPayload(BaseModel):
    """Portable KPI definitions independent of BI/platform bindings."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    metrics: list[MetricDefinition] = Field(min_length=1)


class ReviewPackagePayload(BaseModel):
    """Consolidated review bundle pinning artefact versions and evidence."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    pinned_artefacts: list[ArtefactRef] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    traceability_notes: list[str] = Field(default_factory=list)
    validation_results: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    decision_state: Literal["draft", "pending_review", "approved", "rejected"] = "draft"


PAYLOAD_MODEL_BY_TYPE: dict[ArtefactType, type[BaseModel]] = {
    ArtefactType.BUSINESS_REQUIREMENT: BusinessRequirementPayload,
    ArtefactType.TECHNICAL_REQUIREMENT: TechnicalRequirementPayload,
    ArtefactType.SEMANTIC_MODEL: SemanticModelPayload,
    ArtefactType.DATA_MODEL: DataModelPayload,
    ArtefactType.PIPELINE_SPECIFICATION: PipelineSpecificationPayload,
    ArtefactType.METRIC_DEFINITIONS: MetricDefinitionsPayload,
    ArtefactType.REVIEW_PACKAGE: ReviewPackagePayload,
}


def validate_artefact_payload(
    artefact_type: ArtefactType | str,
    payload: dict[str, Any],
) -> BaseModel:
    """Validate ``payload`` against the schema for ``artefact_type``."""
    kind = ArtefactType(artefact_type)
    model = PAYLOAD_MODEL_BY_TYPE[kind]
    return model.model_validate(payload)


class CanonicalArtefact(BaseModel):
    """Versioned artefact envelope stored via ArtefactStore."""

    model_config = ConfigDict(extra="forbid")

    artefact_id: UUID
    run_id: UUID
    artefact_type: ArtefactType
    version: int = Field(ge=1)
    payload: dict[str, Any]
    created_at: datetime
    created_by: str | None = None
    governance_metadata: GovernanceMetadata | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)
    parent_versions: list[ArtefactRef] = Field(default_factory=list)

    @field_validator("artefact_type", mode="before")
    @classmethod
    def _coerce_artefact_type(cls, value: object) -> object:
        if isinstance(value, ArtefactType):
            return value
        if isinstance(value, str):
            return ArtefactType(value)
        return value

    def to_ref(self) -> ArtefactRef:
        return ArtefactRef(
            artefact_id=self.artefact_id,
            artefact_type=self.artefact_type,
            version=self.version,
            run_id=self.run_id,
        )
