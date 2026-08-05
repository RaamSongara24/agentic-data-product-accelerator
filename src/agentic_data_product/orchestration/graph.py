"""M3 LangGraph: BR intake → Technical Requirement HITL → Mapping subgraph HITL."""

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

from agentic_data_product.agents.requirements import generate_technical_requirement
from agentic_data_product.domain.artefacts import (
    ArtefactRef,
    BusinessRequirementPayload,
)
from agentic_data_product.domain.enums import ArtefactType, ReviewDecisionKind
from agentic_data_product.domain.lineage import CreateLineageEdgeRequest
from agentic_data_product.integrations.llm import create_llm_client
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

# Re-export for runner / tests
__all__ = [
    "CONFIGURABLE_SESSION_FACTORY",
    "build_hitl_graph",
    "compile_hitl_graph",
    "route_after_mapping_review",
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
) -> Literal["mapping_discovery", "approved", "terminated"]:
    decision = state.get("decision")
    if decision == ReviewDecisionKind.APPROVE:
        return "approved"
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


async def mark_approved(state: HitlGraphState) -> dict[str, Any]:
    logger.info("Run %s approved through mapping stage (M3 exit)", state["run_id"])
    return {"decision": ReviewDecisionKind.APPROVE}


async def mark_terminated(state: HitlGraphState) -> dict[str, Any]:
    logger.info("Run %s terminated at HITL gate", state["run_id"])
    return {"decision": ReviewDecisionKind.REJECT}


def build_hitl_graph() -> StateGraph[HitlGraphState, None, HitlGraphState, HitlGraphState]:
    """Construct the uncompiled M3 requirements + mapping graph."""
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
