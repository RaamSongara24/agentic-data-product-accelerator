"""Implementation path: Pipeline Specification → validate → Metric Definitions."""

from __future__ import annotations

import logging
from typing import Any, cast
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agentic_data_product.agents.engineer import generate_pipeline_specification
from agentic_data_product.agents.metrics import generate_metric_definitions
from agentic_data_product.agents.pipeline_validation import validate_pipeline_specification
from agentic_data_product.domain.artefacts import (
    ArtefactRef,
    DataModelPayload,
    PipelineSpecificationPayload,
    SemanticModelPayload,
    TechnicalRequirementPayload,
)
from agentic_data_product.domain.enums import ArtefactType
from agentic_data_product.domain.lineage import CreateLineageEdgeRequest
from agentic_data_product.integrations.llm import create_llm_client
from agentic_data_product.orchestration.mapping.subgraph import CONFIGURABLE_SESSION_FACTORY
from agentic_data_product.orchestration.state import HitlGraphState
from agentic_data_product.persistence.store import PostgresArtefactStore

logger = logging.getLogger(__name__)


def _session_factory(config: RunnableConfig) -> async_sessionmaker[AsyncSession]:
    configurable = config.get("configurable") or {}
    factory = configurable.get(CONFIGURABLE_SESSION_FACTORY)
    if factory is None:
        msg = "Graph config missing session_factory (ArtefactStore session maker)"
        raise RuntimeError(msg)
    return cast(async_sessionmaker[AsyncSession], factory)


async def generate_pipeline_node(
    state: HitlGraphState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Engineer Agent: persist Pipeline Specification."""
    session_factory = _session_factory(config)
    run_id = UUID(state["run_id"])
    tr = TechnicalRequirementPayload.model_validate(state.get("tr_payload") or {})
    semantic = SemanticModelPayload.model_validate(state.get("sm_payload") or {})
    data_model = DataModelPayload.model_validate(state.get("dm_payload") or {})
    llm = create_llm_client()
    pipeline = await generate_pipeline_specification(
        tr=tr,
        semantic=semantic,
        data_model=data_model,
        llm=llm,
        feedback=None,
    )

    parent_versions: list[ArtefactRef] = []
    for parent_id, parent_ver, parent_type in (
        (
            state.get("sm_artefact_id"),
            state.get("sm_artefact_version"),
            ArtefactType.SEMANTIC_MODEL,
        ),
        (
            state.get("dm_artefact_id"),
            state.get("dm_artefact_version"),
            ArtefactType.DATA_MODEL,
        ),
    ):
        if parent_id and parent_ver is not None:
            parent_versions.append(
                ArtefactRef(
                    artefact_id=UUID(str(parent_id)),
                    artefact_type=parent_type,
                    version=int(parent_ver),
                    run_id=run_id,
                )
            )

    existing_id = UUID(state["pipeline_artefact_id"]) if state.get("pipeline_artefact_id") else None

    async with session_factory() as session:
        store = PostgresArtefactStore(session)
        artefact = await store.save_artefact(
            run_id=run_id,
            artefact_type=ArtefactType.PIPELINE_SPECIFICATION,
            payload=pipeline.model_dump(mode="json"),
            artefact_id=existing_id,
            created_by=state.get("created_by"),
            parent_versions=cast(list[ArtefactRef | dict[str, Any]], parent_versions),
            validate_payload=True,
        )
        for parent in parent_versions:
            await store.create_lineage_edge(
                CreateLineageEdgeRequest(
                    run_id=run_id,
                    from_artefact_id=parent.artefact_id,
                    from_version=parent.version,
                    to_artefact_id=artefact.artefact_id,
                    to_version=artefact.version,
                    relationship="derived_from",
                )
            )

    logger.info(
        "Generated Pipeline Specification run_id=%s artefact_id=%s v%s",
        run_id,
        artefact.artefact_id,
        artefact.version,
    )
    return {
        "pipeline_artefact_id": str(artefact.artefact_id),
        "pipeline_artefact_version": artefact.version,
        "pipeline_payload": pipeline.model_dump(mode="json"),
        "decision": None,
    }


async def validate_pipeline_node(
    state: HitlGraphState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Static validation of Pipeline Specification; results feed Review Package."""
    _ = config
    raw = state.get("pipeline_payload")
    if not raw:
        msg = "Pipeline Specification payload missing from graph state"
        raise RuntimeError(msg)
    pipeline = PipelineSpecificationPayload.model_validate(raw)
    results = validate_pipeline_specification(pipeline)
    logger.info(
        "Pipeline static validation run_id=%s results=%s",
        state["run_id"],
        len(results),
    )
    return {"pipeline_validation_results": results}


async def generate_metrics_node(
    state: HitlGraphState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Metrics Agent: persist Metric Definitions (HITL pending artefact)."""
    session_factory = _session_factory(config)
    run_id = UUID(state["run_id"])
    semantic = SemanticModelPayload.model_validate(state.get("sm_payload") or {})
    tr_raw = state.get("tr_payload")
    tr = TechnicalRequirementPayload.model_validate(tr_raw) if tr_raw else None
    llm = create_llm_client()
    metrics = await generate_metric_definitions(
        semantic=semantic,
        tr=tr,
        llm=llm,
        feedback=state.get("feedback"),
    )

    parent_versions: list[ArtefactRef] = []
    sm_id = state.get("sm_artefact_id")
    sm_ver = state.get("sm_artefact_version")
    if sm_id and sm_ver is not None:
        parent_versions.append(
            ArtefactRef(
                artefact_id=UUID(str(sm_id)),
                artefact_type=ArtefactType.SEMANTIC_MODEL,
                version=int(sm_ver),
                run_id=run_id,
            )
        )
    pipe_id = state.get("pipeline_artefact_id")
    pipe_ver = state.get("pipeline_artefact_version")
    if pipe_id and pipe_ver is not None:
        parent_versions.append(
            ArtefactRef(
                artefact_id=UUID(str(pipe_id)),
                artefact_type=ArtefactType.PIPELINE_SPECIFICATION,
                version=int(pipe_ver),
                run_id=run_id,
            )
        )

    artefact_id = UUID(state["metrics_artefact_id"]) if state.get("metrics_artefact_id") else None

    async with session_factory() as session:
        store = PostgresArtefactStore(session)
        artefact = await store.save_artefact(
            run_id=run_id,
            artefact_type=ArtefactType.METRIC_DEFINITIONS,
            payload=metrics.model_dump(mode="json"),
            artefact_id=artefact_id,
            created_by=state.get("created_by"),
            parent_versions=cast(list[ArtefactRef | dict[str, Any]], parent_versions),
            validate_payload=True,
        )
        for parent in parent_versions:
            await store.create_lineage_edge(
                CreateLineageEdgeRequest(
                    run_id=run_id,
                    from_artefact_id=parent.artefact_id,
                    from_version=parent.version,
                    to_artefact_id=artefact.artefact_id,
                    to_version=artefact.version,
                    relationship="derived_from",
                )
            )

    logger.info(
        "Generated Metric Definitions run_id=%s artefact_id=%s v%s",
        run_id,
        artefact.artefact_id,
        artefact.version,
    )
    return {
        "metrics_artefact_id": str(artefact.artefact_id),
        "metrics_artefact_version": artefact.version,
        "metrics_payload": metrics.model_dump(mode="json"),
        "artefact_id": str(artefact.artefact_id),
        "artefact_version": artefact.version,
        "artefact_type": ArtefactType.METRIC_DEFINITIONS.value,
        "review_stage": "implementation",
        "decision": None,
    }
