"""LangGraph state schema for the full seven-artefact HITL workflow."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class HitlGraphState(TypedDict):
    """Control-plane state held in the checkpointer (artefact bodies live in the store)."""

    run_id: str
    title: NotRequired[str | None]
    created_by: NotRequired[str | None]
    user_id: NotRequired[str | None]
    accessible_object_ids: NotRequired[list[str] | None]
    seed_payload: NotRequired[dict[str, Any] | None]
    feedback: NotRequired[str | None]

    # Current HITL artefact pointer
    artefact_id: NotRequired[str | None]
    artefact_version: NotRequired[int | None]
    artefact_type: NotRequired[str | None]
    review_stage: NotRequired[str | None]
    decision: NotRequired[str | None]

    # Business Requirement
    br_artefact_id: NotRequired[str | None]
    br_artefact_version: NotRequired[int | None]
    br_payload: NotRequired[dict[str, Any] | None]

    # Technical Requirement
    tr_artefact_id: NotRequired[str | None]
    tr_artefact_version: NotRequired[int | None]
    tr_payload: NotRequired[dict[str, Any] | None]

    # Mapping subgraph
    discovered_objects: NotRequired[list[dict[str, Any]] | None]
    discovered_object_ids: NotRequired[list[str] | None]
    mapping_proposal: NotRequired[dict[str, Any] | None]
    mapping_artefact_id: NotRequired[str | None]
    mapping_artefact_version: NotRequired[int | None]
    schema_retry_count: NotRequired[int]
    logic_retry_count: NotRequired[int]
    judge_notes: NotRequired[str | None]
    judge_outcome: NotRequired[str | None]
    mapping_escalated: NotRequired[bool]
    mapping_stage: NotRequired[str | None]

    # Modelling
    sm_artefact_id: NotRequired[str | None]
    sm_artefact_version: NotRequired[int | None]
    sm_payload: NotRequired[dict[str, Any] | None]
    dm_artefact_id: NotRequired[str | None]
    dm_artefact_version: NotRequired[int | None]
    dm_payload: NotRequired[dict[str, Any] | None]

    # Implementation path
    pipeline_artefact_id: NotRequired[str | None]
    pipeline_artefact_version: NotRequired[int | None]
    pipeline_payload: NotRequired[dict[str, Any] | None]
    pipeline_validation_results: NotRequired[list[str] | None]
    metrics_artefact_id: NotRequired[str | None]
    metrics_artefact_version: NotRequired[int | None]
    metrics_payload: NotRequired[dict[str, Any] | None]

    # Review Package
    rp_artefact_id: NotRequired[str | None]
    rp_artefact_version: NotRequired[int | None]
    rp_payload: NotRequired[dict[str, Any] | None]

    # Test hooks (never secrets)
    force_judge_outcome: NotRequired[str | None]
    force_empty_mapping_sources: NotRequired[bool]
