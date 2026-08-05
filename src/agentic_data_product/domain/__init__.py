"""Canonical domain models for artefacts, runs, audit, and lineage.

Milestone M1 introduces typed Pydantic contracts for the seven canonical
artefacts plus supporting run / audit / lineage types. Orchestration and
HITL remain out of scope until M2.
"""

from agentic_data_product.domain.artefacts import (
    PAYLOAD_MODEL_BY_TYPE,
    ArtefactRef,
    BusinessRequirementPayload,
    CanonicalArtefact,
    DataModelPayload,
    GovernanceMetadata,
    MetricDefinitionsPayload,
    PipelineSpecificationPayload,
    ReviewPackagePayload,
    SemanticModelPayload,
    SourceRef,
    TechnicalRequirementPayload,
    validate_artefact_payload,
)
from agentic_data_product.domain.audit import AuditEvent
from agentic_data_product.domain.enums import ArtefactType, AuditAction, RunStatus
from agentic_data_product.domain.lineage import CreateLineageEdgeRequest, LineageEdge
from agentic_data_product.domain.run import CreateWorkflowRunRequest, WorkflowRun

__all__ = [
    "PAYLOAD_MODEL_BY_TYPE",
    "ArtefactRef",
    "ArtefactType",
    "AuditAction",
    "AuditEvent",
    "BusinessRequirementPayload",
    "CanonicalArtefact",
    "CreateLineageEdgeRequest",
    "CreateWorkflowRunRequest",
    "DataModelPayload",
    "GovernanceMetadata",
    "LineageEdge",
    "MetricDefinitionsPayload",
    "PipelineSpecificationPayload",
    "ReviewPackagePayload",
    "RunStatus",
    "SemanticModelPayload",
    "SourceRef",
    "TechnicalRequirementPayload",
    "WorkflowRun",
    "validate_artefact_payload",
]
