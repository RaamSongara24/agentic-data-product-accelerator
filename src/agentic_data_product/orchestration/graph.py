"""M2 HITL stub LangGraph: generate → interrupt review → approve/reject/revisions."""

from __future__ import annotations

import logging
from typing import Any, Literal
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agentic_data_product.domain.artefacts import BusinessRequirementPayload
from agentic_data_product.domain.enums import ArtefactType, ReviewDecisionKind
from agentic_data_product.orchestration.state import HitlGraphState
from agentic_data_product.persistence.store import PostgresArtefactStore

logger = logging.getLogger(__name__)

CONFIGURABLE_SESSION_FACTORY = "session_factory"


def _default_stub_payload(
    *,
    title: str | None,
    feedback: str | None,
    version_hint: int,
) -> dict[str, Any]:
    """Build a deterministic Business Requirement stub (no LLM)."""
    base_title = title or "Stub business requirement"
    notes = None
    if feedback:
        notes = f"Revision notes from reviewer: {feedback}"
    payload = BusinessRequirementPayload(
        title=f"{base_title} (v{version_hint})",
        intent=(
            "Demonstrate durable HITL interrupt/resume on a stub artefact "
            "for the Agentic Data Product Design Platform."
        ),
        objectives=[
            "Produce a versioned canonical Business Requirement stub",
            "Pause for Approve / Reject / Request revisions",
        ],
        constraints=["M2 stub only — no LLM generation"],
        success_criteria=[
            "Run reaches waiting_for_review with a persisted artefact",
            "All three HITL decisions behave per ADR 005",
        ],
        stakeholders=["data_consultant"],
        notes=notes,
    )
    return payload.model_dump(mode="json")


async def generate_stub(state: HitlGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Generator node: persist a new Business Requirement version via ArtefactStore."""
    configurable = config.get("configurable") or {}
    session_factory: async_sessionmaker[AsyncSession] | None = configurable.get(
        CONFIGURABLE_SESSION_FACTORY
    )
    if session_factory is None:
        msg = "Graph config missing session_factory (ArtefactStore session maker)"
        raise RuntimeError(msg)

    run_id = UUID(state["run_id"])
    previous_version = state.get("artefact_version") or 0
    next_version = previous_version + 1
    feedback = state.get("feedback")
    seed = state.get("seed_payload")
    if seed:
        payload = dict(seed)
        if feedback:
            existing_notes = payload.get("notes") or ""
            revision_note = f"Revision notes from reviewer: {feedback}"
            payload["notes"] = (
                f"{existing_notes}\n{revision_note}".strip() if existing_notes else revision_note
            )
    else:
        payload = _default_stub_payload(
            title=state.get("title"),
            feedback=feedback,
            version_hint=next_version,
        )

    async with session_factory() as session:
        store = PostgresArtefactStore(session)
        artefact = await store.save_artefact(
            run_id=run_id,
            artefact_type=ArtefactType.BUSINESS_REQUIREMENT,
            payload=payload,
            created_by=state.get("created_by"),
            validate_payload=True,
        )

    logger.info(
        "Generated stub artefact run_id=%s artefact_id=%s version=%s",
        run_id,
        artefact.artefact_id,
        artefact.version,
    )
    return {
        "artefact_id": str(artefact.artefact_id),
        "artefact_version": artefact.version,
        "artefact_type": str(artefact.artefact_type.value),
        "decision": None,
    }


async def await_review(state: HitlGraphState) -> dict[str, Any]:
    """HITL interrupt node — resumes with a ReviewDecisionKind payload."""
    resume_value = interrupt(
        {
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


def route_after_review(
    state: HitlGraphState,
) -> Literal["generate_stub", "approved", "terminated"]:
    decision = state.get("decision")
    if decision == ReviewDecisionKind.APPROVE:
        return "approved"
    if decision == ReviewDecisionKind.REJECT:
        return "terminated"
    if decision == ReviewDecisionKind.REQUEST_REVISIONS:
        return "generate_stub"
    msg = f"Unknown or missing review decision: {decision!r}"
    raise ValueError(msg)


async def mark_approved(state: HitlGraphState) -> dict[str, Any]:
    logger.info("Run %s approved at HITL gate", state["run_id"])
    return {"decision": ReviewDecisionKind.APPROVE}


async def mark_terminated(state: HitlGraphState) -> dict[str, Any]:
    logger.info("Run %s terminated at HITL gate", state["run_id"])
    return {"decision": ReviewDecisionKind.REJECT}


def build_hitl_graph() -> StateGraph[HitlGraphState, None, HitlGraphState, HitlGraphState]:
    """Construct the uncompiled M2 HITL stub graph."""
    graph: StateGraph[HitlGraphState, None, HitlGraphState, HitlGraphState] = StateGraph(
        HitlGraphState
    )
    graph.add_node("generate_stub", generate_stub)
    graph.add_node("await_review", await_review)
    graph.add_node("approved", mark_approved)
    graph.add_node("terminated", mark_terminated)

    graph.add_edge(START, "generate_stub")
    graph.add_edge("generate_stub", "await_review")
    graph.add_conditional_edges(
        "await_review",
        route_after_review,
        {
            "generate_stub": "generate_stub",
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
