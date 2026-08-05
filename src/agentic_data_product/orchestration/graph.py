"""M4 LangGraph: BR → TR HITL → Mapping HITL → Modelling HITL → Impl HITL → RP HITL."""

from __future__ import annotations

import logging
from typing import Any, Literal, cast
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agentic_data_product.agents.modelling import generate_modelling_artefacts
from agentic_data_product.agents.requirements import generate_technical_requirement
from agentic_data_product.agents.review_package import assemble_review_package
from agentic_data_product.domain.artefacts import (
    ArtefactRef,
    BusinessRequirementPayload,
    DataModelPayload,
    ReviewPackagePayload,
    SourceRef,
    TechnicalRequirementPayload,
    validate_artefact_payload,
)
from agentic_data_product.domain.enums import ArtefactType, ReviewDecisionKind
from agentic_data_product.domain.lineage import CreateLineageEdgeRequest
from agentic_data_product.integrations.llm import create_llm_client
from agentic_data_product.orchestration.implementation.subgraph import (
    generate_metrics_node,
    generate_pipeline_node,
    validate_pipeline_node,
)
from agentic_data_product.orchestration.mapping.subgraph import (
    CONFIGURABLE_SESSION_FACTORY,
    data_mapping_node,
    discovery_node,
    mapping_judge_node,
    persist_mapping_node,
    route_after_judge,
)
from agentic_data_product.orchestration.state import HitlGraphState
from agentic_data_product.persistence.store import PostgresArtefactStore

logger = logging.getLogger(__name__)

__all__ = [
    "CONFIGURABLE_SESSION_FACTORY",
    "build_hitl_graph",
    "compile_hitl_graph",
    "route_after_implementation_review",
    "route_after_mapping_review",
    "route_after_modelling_review",
    "route_after_rp_review",
    "route_after_tr_review",
]


def _session_factory(config: RunnableConfig) -> async_sessionmaker[AsyncSession]:
    configurable = config.get("configurable") or {}
    factory = configurable.get(CONFIGURABLE_SESSION_FACTORY)
    if factory is None:
        msg = "Graph config missing session_factory (ArtefactStore session maker)"
        raise RuntimeError(msg)
    return cast(async_sessionmaker[AsyncSession], factory)


def _default_business_requirement(*, title: str | None) -> BusinessRequirementPayload:
    return BusinessRequirementPayload(
        title=title or "Sales analytics data product",
        intent=(
            "Deliver a governed sales analytics data product covering orders, "
            "customers, and products for consultant-led design."
        ),
        objectives=[
            "Analyse order amounts and order counts by customer and region",
            "Support product-level sales reporting",
        ],
        constraints=[
            "Must not use HR or security datasets the consultant cannot access",
            "Outputs must remain technology-agnostic canonical artefacts",
        ],
        success_criteria=[
            "Technical Requirement approved via HITL",
            "Mapping data-model slice approved via HITL",
            "All seven canonical artefacts approved via Review Package",
        ],
        stakeholders=["data_consultant"],
        notes=None,
    )


async def ensure_business_requirement(
    state: HitlGraphState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Persist the intake Business Requirement (consultant-authored; no BR HITL)."""
    session_factory = _session_factory(config)
    run_id = UUID(state["run_id"])
    seed = state.get("seed_payload")
    if seed:
        payload = BusinessRequirementPayload.model_validate(seed)
    else:
        payload = _default_business_requirement(title=state.get("title"))

    async with session_factory() as session:
        store = PostgresArtefactStore(session)
        artefact = await store.save_artefact(
            run_id=run_id,
            artefact_type=ArtefactType.BUSINESS_REQUIREMENT,
            payload=payload.model_dump(mode="json"),
            created_by=state.get("created_by"),
            validate_payload=True,
        )

    logger.info(
        "Persisted Business Requirement run_id=%s artefact_id=%s v%s",
        run_id,
        artefact.artefact_id,
        artefact.version,
    )
    return {
        "br_artefact_id": str(artefact.artefact_id),
        "br_artefact_version": artefact.version,
        "br_payload": payload.model_dump(mode="json"),
        "decision": None,
        "feedback": None,
        "schema_retry_count": 0,
        "logic_retry_count": 0,
        "mapping_escalated": False,
    }


async def generate_technical_requirement_node(
    state: HitlGraphState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Requirements Agent: BR → Technical Requirement (versioned)."""
    session_factory = _session_factory(config)
    run_id = UUID(state["run_id"])
    br_raw = state.get("br_payload")
    if not br_raw:
        msg = "Business Requirement payload missing from graph state"
        raise RuntimeError(msg)
    br = BusinessRequirementPayload.model_validate(br_raw)
    llm = create_llm_client()
    tr = await generate_technical_requirement(
        br,
        llm=llm,
        feedback=state.get("feedback"),
    )

    parent_versions: list[ArtefactRef] = []
    br_id = state.get("br_artefact_id")
    br_ver = state.get("br_artefact_version")
    if br_id and br_ver is not None:
        parent_versions.append(
            ArtefactRef(
                artefact_id=UUID(str(br_id)),
                artefact_type=ArtefactType.BUSINESS_REQUIREMENT,
                version=int(br_ver),
                run_id=run_id,
            )
        )

    artefact_id = UUID(state["tr_artefact_id"]) if state.get("tr_artefact_id") else None

    async with session_factory() as session:
        store = PostgresArtefactStore(session)
        artefact = await store.save_artefact(
            run_id=run_id,
            artefact_type=ArtefactType.TECHNICAL_REQUIREMENT,
            payload=tr.model_dump(mode="json"),
            artefact_id=artefact_id,
            created_by=state.get("created_by"),
            parent_versions=cast(list[ArtefactRef | dict[str, Any]], parent_versions),
            validate_payload=True,
        )
        if parent_versions:
            parent = parent_versions[0]
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
        "Generated Technical Requirement run_id=%s artefact_id=%s v%s",
        run_id,
        artefact.artefact_id,
        artefact.version,
    )
    return {
        "tr_artefact_id": str(artefact.artefact_id),
        "tr_artefact_version": artefact.version,
        "tr_payload": tr.model_dump(mode="json"),
        "artefact_id": str(artefact.artefact_id),
        "artefact_version": artefact.version,
        "artefact_type": ArtefactType.TECHNICAL_REQUIREMENT.value,
        "review_stage": "technical_requirement",
        "decision": None,
    }


async def await_tr_review(state: HitlGraphState) -> dict[str, Any]:
    """HITL interrupt after Technical Requirement."""
    resume_value = interrupt(
        {
            "stage": "technical_requirement",
            "artefact_id": state.get("artefact_id"),
            "artefact_version": state.get("artefact_version"),
            "artefact_type": state.get("artefact_type"),
            "feedback": state.get("feedback"),
        }
    )
    if not isinstance(resume_value, dict):
        msg = f"Expected review decision dict on resume, got {type(resume_value)!r}"
        raise TypeError(msg)
    decision = str(resume_value.get("decision", ""))
    comments = str(resume_value.get("comments") or "")
    return {
        "decision": decision,
        "feedback": comments if decision == ReviewDecisionKind.REQUEST_REVISIONS else None,
    }


def route_after_tr_review(
    state: HitlGraphState,
) -> Literal["generate_tr", "mapping_discovery", "terminated"]:
    decision = state.get("decision")
    if decision == ReviewDecisionKind.APPROVE:
        return "mapping_discovery"
    if decision == ReviewDecisionKind.REJECT:
        return "terminated"
    if decision == ReviewDecisionKind.REQUEST_REVISIONS:
        return "generate_tr"
    msg = f"Unknown or missing review decision: {decision!r}"
    raise ValueError(msg)


async def await_mapping_review(state: HitlGraphState) -> dict[str, Any]:
    """HITL interrupt after mapping / data-model slice."""
    resume_value = interrupt(
        {
            "stage": "mapping",
            "artefact_id": state.get("artefact_id"),
            "artefact_version": state.get("artefact_version"),
            "artefact_type": state.get("artefact_type"),
            "judge_notes": state.get("judge_notes"),
            "mapping_escalated": state.get("mapping_escalated"),
            "feedback": state.get("feedback"),
        }
    )
    if not isinstance(resume_value, dict):
        msg = f"Expected review decision dict on resume, got {type(resume_value)!r}"
        raise TypeError(msg)
    decision = str(resume_value.get("decision", ""))
    comments = str(resume_value.get("comments") or "")
    return {
        "decision": decision,
        "feedback": comments if decision == ReviewDecisionKind.REQUEST_REVISIONS else None,
    }


def route_after_mapping_review(
    state: HitlGraphState,
) -> Literal["mapping_discovery", "modelling", "terminated"]:
    decision = state.get("decision")
    if decision == ReviewDecisionKind.APPROVE:
        return "modelling"
    if decision == ReviewDecisionKind.REJECT:
        return "terminated"
    if decision == ReviewDecisionKind.REQUEST_REVISIONS:
        return "mapping_discovery"
    msg = f"Unknown or missing review decision: {decision!r}"
    raise ValueError(msg)


async def reset_mapping_retries(state: HitlGraphState) -> dict[str, Any]:
    """Clear mapping retry counters when (re)entering the mapping subgraph."""
    _ = state
    return {
        "schema_retry_count": 0,
        "logic_retry_count": 0,
        "mapping_escalated": False,
        "judge_notes": None,
        "judge_outcome": None,
        "decision": None,
    }


async def generate_modelling_node(
    state: HitlGraphState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Modelling Agent: Semantic Model + enriched Data Model; HITL pending = Semantic Model."""
    session_factory = _session_factory(config)
    run_id = UUID(state["run_id"])
    tr_raw = state.get("tr_payload")
    if not tr_raw:
        msg = "Technical Requirement payload missing from graph state"
        raise RuntimeError(msg)
    tr = TechnicalRequirementPayload.model_validate(tr_raw)

    mapping_dm: DataModelPayload | None = None
    mapping_source_refs: list[SourceRef] = []
    mapping_id = state.get("mapping_artefact_id")
    mapping_ver = state.get("mapping_artefact_version")
    async with session_factory() as session:
        store = PostgresArtefactStore(session)
        if mapping_id and mapping_ver is not None:
            mapping_art = await store.get_artefact(UUID(str(mapping_id)), int(mapping_ver))
            mapping_dm = DataModelPayload.model_validate(mapping_art.payload)
            mapping_source_refs = list(mapping_art.source_refs)

    llm = create_llm_client()
    semantic, data_model = await generate_modelling_artefacts(
        tr,
        mapping_data_model=mapping_dm,
        llm=llm,
        feedback=state.get("feedback"),
    )

    parent_versions: list[ArtefactRef] = []
    tr_id = state.get("tr_artefact_id")
    tr_ver = state.get("tr_artefact_version")
    if tr_id and tr_ver is not None:
        parent_versions.append(
            ArtefactRef(
                artefact_id=UUID(str(tr_id)),
                artefact_type=ArtefactType.TECHNICAL_REQUIREMENT,
                version=int(tr_ver),
                run_id=run_id,
            )
        )
    if mapping_id and mapping_ver is not None:
        parent_versions.append(
            ArtefactRef(
                artefact_id=UUID(str(mapping_id)),
                artefact_type=ArtefactType.DATA_MODEL,
                version=int(mapping_ver),
                run_id=run_id,
            )
        )

    # Continue the same Data Model artefact id from mapping when present.
    dm_artefact_id = (
        UUID(str(mapping_id))
        if mapping_id
        else (UUID(state["dm_artefact_id"]) if state.get("dm_artefact_id") else None)
    )
    sm_artefact_id = UUID(state["sm_artefact_id"]) if state.get("sm_artefact_id") else None

    async with session_factory() as session:
        store = PostgresArtefactStore(session)
        dm_artefact = await store.save_artefact(
            run_id=run_id,
            artefact_type=ArtefactType.DATA_MODEL,
            payload=data_model.model_dump(mode="json"),
            artefact_id=dm_artefact_id,
            created_by=state.get("created_by"),
            source_refs=cast(list[SourceRef | dict[str, Any]], mapping_source_refs),
            parent_versions=cast(list[ArtefactRef | dict[str, Any]], parent_versions),
            governance_metadata=data_model.governance_metadata,
            validate_payload=True,
        )
        for parent in parent_versions:
            await store.create_lineage_edge(
                CreateLineageEdgeRequest(
                    run_id=run_id,
                    from_artefact_id=parent.artefact_id,
                    from_version=parent.version,
                    to_artefact_id=dm_artefact.artefact_id,
                    to_version=dm_artefact.version,
                    relationship="derived_from",
                )
            )

        sm_parents: list[ArtefactRef] = list(parent_versions)
        sm_parents.append(
            ArtefactRef(
                artefact_id=dm_artefact.artefact_id,
                artefact_type=ArtefactType.DATA_MODEL,
                version=dm_artefact.version,
                run_id=run_id,
            )
        )
        sm_artefact = await store.save_artefact(
            run_id=run_id,
            artefact_type=ArtefactType.SEMANTIC_MODEL,
            payload=semantic.model_dump(mode="json"),
            artefact_id=sm_artefact_id,
            created_by=state.get("created_by"),
            parent_versions=cast(list[ArtefactRef | dict[str, Any]], sm_parents),
            validate_payload=True,
        )
        for parent in sm_parents:
            await store.create_lineage_edge(
                CreateLineageEdgeRequest(
                    run_id=run_id,
                    from_artefact_id=parent.artefact_id,
                    from_version=parent.version,
                    to_artefact_id=sm_artefact.artefact_id,
                    to_version=sm_artefact.version,
                    relationship="derived_from",
                )
            )

    logger.info(
        "Generated modelling artefacts run_id=%s sm=%s v%s dm=%s v%s",
        run_id,
        sm_artefact.artefact_id,
        sm_artefact.version,
        dm_artefact.artefact_id,
        dm_artefact.version,
    )
    return {
        "sm_artefact_id": str(sm_artefact.artefact_id),
        "sm_artefact_version": sm_artefact.version,
        "sm_payload": semantic.model_dump(mode="json"),
        "dm_artefact_id": str(dm_artefact.artefact_id),
        "dm_artefact_version": dm_artefact.version,
        "dm_payload": data_model.model_dump(mode="json"),
        "mapping_artefact_id": str(dm_artefact.artefact_id),
        "mapping_artefact_version": dm_artefact.version,
        "artefact_id": str(sm_artefact.artefact_id),
        "artefact_version": sm_artefact.version,
        "artefact_type": ArtefactType.SEMANTIC_MODEL.value,
        "review_stage": "modelling",
        "decision": None,
    }


async def await_modelling_review(state: HitlGraphState) -> dict[str, Any]:
    """HITL interrupt after Semantic Model + Data Model."""
    resume_value = interrupt(
        {
            "stage": "modelling",
            "artefact_id": state.get("artefact_id"),
            "artefact_version": state.get("artefact_version"),
            "artefact_type": state.get("artefact_type"),
            "feedback": state.get("feedback"),
        }
    )
    if not isinstance(resume_value, dict):
        msg = f"Expected review decision dict on resume, got {type(resume_value)!r}"
        raise TypeError(msg)
    decision = str(resume_value.get("decision", ""))
    comments = str(resume_value.get("comments") or "")
    return {
        "decision": decision,
        "feedback": comments if decision == ReviewDecisionKind.REQUEST_REVISIONS else None,
    }


def route_after_modelling_review(
    state: HitlGraphState,
) -> Literal["modelling", "implementation", "terminated"]:
    decision = state.get("decision")
    if decision == ReviewDecisionKind.APPROVE:
        return "implementation"
    if decision == ReviewDecisionKind.REJECT:
        return "terminated"
    if decision == ReviewDecisionKind.REQUEST_REVISIONS:
        return "modelling"
    msg = f"Unknown or missing review decision: {decision!r}"
    raise ValueError(msg)


async def await_implementation_review(state: HitlGraphState) -> dict[str, Any]:
    """HITL interrupt after Pipeline Spec + Metric Definitions (pending = metrics)."""
    resume_value = interrupt(
        {
            "stage": "implementation",
            "artefact_id": state.get("artefact_id"),
            "artefact_version": state.get("artefact_version"),
            "artefact_type": state.get("artefact_type"),
            "pipeline_validation_results": state.get("pipeline_validation_results"),
            "feedback": state.get("feedback"),
        }
    )
    if not isinstance(resume_value, dict):
        msg = f"Expected review decision dict on resume, got {type(resume_value)!r}"
        raise TypeError(msg)
    decision = str(resume_value.get("decision", ""))
    comments = str(resume_value.get("comments") or "")
    return {
        "decision": decision,
        "feedback": comments if decision == ReviewDecisionKind.REQUEST_REVISIONS else None,
    }


def route_after_implementation_review(
    state: HitlGraphState,
) -> Literal["generate_metrics", "assemble_rp", "terminated"]:
    """Request revisions regenerates Metric Definitions only (M4 AC)."""
    decision = state.get("decision")
    if decision == ReviewDecisionKind.APPROVE:
        return "assemble_rp"
    if decision == ReviewDecisionKind.REJECT:
        return "terminated"
    if decision == ReviewDecisionKind.REQUEST_REVISIONS:
        return "generate_metrics"
    msg = f"Unknown or missing review decision: {decision!r}"
    raise ValueError(msg)


async def assemble_review_package_node(
    state: HitlGraphState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Assemble Review Package pinning all prior artefact versions."""
    session_factory = _session_factory(config)
    run_id = UUID(state["run_id"])
    title = state.get("title") or "data product"

    pinned: list[ArtefactRef] = []
    for parent_id, parent_ver, parent_type in (
        (
            state.get("br_artefact_id"),
            state.get("br_artefact_version"),
            ArtefactType.BUSINESS_REQUIREMENT,
        ),
        (
            state.get("tr_artefact_id"),
            state.get("tr_artefact_version"),
            ArtefactType.TECHNICAL_REQUIREMENT,
        ),
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
        (
            state.get("pipeline_artefact_id"),
            state.get("pipeline_artefact_version"),
            ArtefactType.PIPELINE_SPECIFICATION,
        ),
        (
            state.get("metrics_artefact_id"),
            state.get("metrics_artefact_version"),
            ArtefactType.METRIC_DEFINITIONS,
        ),
    ):
        if parent_id and parent_ver is not None:
            pinned.append(
                ArtefactRef(
                    artefact_id=UUID(str(parent_id)),
                    artefact_type=parent_type,
                    version=int(parent_ver),
                    run_id=run_id,
                )
            )

    package = assemble_review_package(
        title=str(title),
        pinned=pinned,
        validation_results=list(state.get("pipeline_validation_results") or []),
        feedback=state.get("feedback"),
    )

    parent_versions = list(pinned)
    existing_id = UUID(state["rp_artefact_id"]) if state.get("rp_artefact_id") else None

    async with session_factory() as session:
        store = PostgresArtefactStore(session)
        artefact = await store.save_artefact(
            run_id=run_id,
            artefact_type=ArtefactType.REVIEW_PACKAGE,
            payload=package.model_dump(mode="json"),
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
        "Assembled Review Package run_id=%s artefact_id=%s v%s",
        run_id,
        artefact.artefact_id,
        artefact.version,
    )
    return {
        "rp_artefact_id": str(artefact.artefact_id),
        "rp_artefact_version": artefact.version,
        "rp_payload": package.model_dump(mode="json"),
        "artefact_id": str(artefact.artefact_id),
        "artefact_version": artefact.version,
        "artefact_type": ArtefactType.REVIEW_PACKAGE.value,
        "review_stage": "review_package",
        "decision": None,
    }


async def await_rp_review(state: HitlGraphState) -> dict[str, Any]:
    """HITL interrupt after Review Package."""
    resume_value = interrupt(
        {
            "stage": "review_package",
            "artefact_id": state.get("artefact_id"),
            "artefact_version": state.get("artefact_version"),
            "artefact_type": state.get("artefact_type"),
            "feedback": state.get("feedback"),
        }
    )
    if not isinstance(resume_value, dict):
        msg = f"Expected review decision dict on resume, got {type(resume_value)!r}"
        raise TypeError(msg)
    decision = str(resume_value.get("decision", ""))
    comments = str(resume_value.get("comments") or "")
    return {
        "decision": decision,
        "feedback": comments if decision == ReviewDecisionKind.REQUEST_REVISIONS else None,
    }


def route_after_rp_review(
    state: HitlGraphState,
) -> Literal["assemble_rp", "approved", "terminated"]:
    decision = state.get("decision")
    if decision == ReviewDecisionKind.APPROVE:
        return "approved"
    if decision == ReviewDecisionKind.REJECT:
        return "terminated"
    if decision == ReviewDecisionKind.REQUEST_REVISIONS:
        return "assemble_rp"
    msg = f"Unknown or missing review decision: {decision!r}"
    raise ValueError(msg)


async def mark_approved(state: HitlGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Persist Review Package ``decision_state=approved`` then finish the run.

    In-platform publish means the Review Package (and pinned versions) are marked
    approved — not that an adapter has deployed anywhere.
    """
    session_factory = _session_factory(config)
    run_id = UUID(state["run_id"])
    rp_id = state.get("rp_artefact_id") or state.get("artefact_id")
    if rp_id:
        async with session_factory() as session:
            store = PostgresArtefactStore(session)
            current = await store.get_artefact(UUID(str(rp_id)))
            payload = validate_artefact_payload(ArtefactType.REVIEW_PACKAGE, current.payload)
            assert isinstance(payload, ReviewPackagePayload)
            approved = payload.model_copy(
                update={
                    "decision_state": "approved",
                    "summary": f"{payload.summary} — approved in-platform",
                    "recommendations": [
                        *payload.recommendations,
                        "Optional: export approved canonical artefacts via PlatformAdapter "
                        "(Databricks stub) — export is not a live deploy",
                    ],
                }
            )
            artefact = await store.save_artefact(
                run_id=run_id,
                artefact_type=ArtefactType.REVIEW_PACKAGE,
                payload=approved.model_dump(mode="json"),
                artefact_id=current.artefact_id,
                created_by=state.get("created_by"),
                parent_versions=cast(
                    list[ArtefactRef | dict[str, Any]],
                    list(payload.pinned_artefacts),
                ),
                validate_payload=True,
            )
        logger.info(
            "Run %s approved; Review Package %s v%s decision_state=approved",
            run_id,
            artefact.artefact_id,
            artefact.version,
        )
        return {
            "decision": ReviewDecisionKind.APPROVE,
            "rp_artefact_version": artefact.version,
            "artefact_version": artefact.version,
            "rp_payload": approved.model_dump(mode="json"),
        }

    logger.info("Run %s approved through Review Package (M4 exit)", state["run_id"])
    return {"decision": ReviewDecisionKind.APPROVE}


async def mark_terminated(state: HitlGraphState) -> dict[str, Any]:
    logger.info("Run %s terminated at HITL gate", state["run_id"])
    return {"decision": ReviewDecisionKind.REJECT}


def build_hitl_graph() -> StateGraph[HitlGraphState, None, HitlGraphState, HitlGraphState]:
    """Construct the uncompiled M4 seven-artefact HITL graph."""
    graph: StateGraph[HitlGraphState, None, HitlGraphState, HitlGraphState] = StateGraph(
        HitlGraphState
    )

    graph.add_node("ensure_br", ensure_business_requirement)
    graph.add_node("generate_tr", generate_technical_requirement_node)
    graph.add_node("await_tr_review", await_tr_review)
    graph.add_node("reset_mapping_retries", reset_mapping_retries)
    graph.add_node("mapping_discovery", discovery_node)
    graph.add_node("mapping_data_mapping", data_mapping_node)
    graph.add_node("mapping_judge", mapping_judge_node)
    graph.add_node("persist_mapping", persist_mapping_node)
    graph.add_node("await_mapping_review", await_mapping_review)
    graph.add_node("modelling", generate_modelling_node)
    graph.add_node("await_modelling_review", await_modelling_review)
    graph.add_node("generate_pipeline", generate_pipeline_node)
    graph.add_node("validate_pipeline", validate_pipeline_node)
    graph.add_node("generate_metrics", generate_metrics_node)
    graph.add_node("await_implementation_review", await_implementation_review)
    graph.add_node("assemble_rp", assemble_review_package_node)
    graph.add_node("await_rp_review", await_rp_review)
    graph.add_node("approved", mark_approved)
    graph.add_node("terminated", mark_terminated)

    graph.add_edge(START, "ensure_br")
    graph.add_edge("ensure_br", "generate_tr")
    graph.add_edge("generate_tr", "await_tr_review")
    graph.add_conditional_edges(
        "await_tr_review",
        route_after_tr_review,
        {
            "generate_tr": "generate_tr",
            "mapping_discovery": "reset_mapping_retries",
            "terminated": "terminated",
        },
    )
    graph.add_edge("reset_mapping_retries", "mapping_discovery")
    graph.add_edge("mapping_discovery", "mapping_data_mapping")
    graph.add_edge("mapping_data_mapping", "mapping_judge")
    graph.add_conditional_edges(
        "mapping_judge",
        route_after_judge,
        {
            "discovery": "mapping_discovery",
            "data_mapping": "mapping_data_mapping",
            "persist_mapping": "persist_mapping",
        },
    )
    graph.add_edge("persist_mapping", "await_mapping_review")
    graph.add_conditional_edges(
        "await_mapping_review",
        route_after_mapping_review,
        {
            "mapping_discovery": "reset_mapping_retries",
            "modelling": "modelling",
            "terminated": "terminated",
        },
    )
    graph.add_edge("modelling", "await_modelling_review")
    graph.add_conditional_edges(
        "await_modelling_review",
        route_after_modelling_review,
        {
            "modelling": "modelling",
            "implementation": "generate_pipeline",
            "terminated": "terminated",
        },
    )
    graph.add_edge("generate_pipeline", "validate_pipeline")
    graph.add_edge("validate_pipeline", "generate_metrics")
    graph.add_edge("generate_metrics", "await_implementation_review")
    graph.add_conditional_edges(
        "await_implementation_review",
        route_after_implementation_review,
        {
            "generate_metrics": "generate_metrics",
            "assemble_rp": "assemble_rp",
            "terminated": "terminated",
        },
    )
    graph.add_edge("assemble_rp", "await_rp_review")
    graph.add_conditional_edges(
        "await_rp_review",
        route_after_rp_review,
        {
            "assemble_rp": "assemble_rp",
            "approved": "approved",
            "terminated": "terminated",
        },
    )
    graph.add_edge("approved", END)
    graph.add_edge("terminated", END)
    return graph


def compile_hitl_graph(
    checkpointer: BaseCheckpointSaver[str],
) -> CompiledStateGraph[HitlGraphState, None, HitlGraphState, HitlGraphState]:
    """Compile the HITL graph with a durable checkpointer."""
    return build_hitl_graph().compile(checkpointer=checkpointer)
