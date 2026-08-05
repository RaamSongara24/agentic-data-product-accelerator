"""Application service that starts and resumes HITL runs against the compiled graph."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agentic_data_product.domain.artefacts import ArtefactRef
from agentic_data_product.domain.enums import ArtefactType, ReviewDecisionKind, RunStatus
from agentic_data_product.domain.review import PendingReview, ReviewDecisionRequest
from agentic_data_product.domain.run import (
    CreateRunApiRequest,
    CreateWorkflowRunRequest,
    RunDetail,
    WorkflowRun,
)
from agentic_data_product.orchestration.graph import CONFIGURABLE_SESSION_FACTORY
from agentic_data_product.orchestration.state import HitlGraphState
from agentic_data_product.persistence.store import (
    ArtefactStoreError,
    ConflictError,
    NotFoundError,
    PostgresArtefactStore,
)

logger = logging.getLogger(__name__)

HitlCompiledGraph = CompiledStateGraph[HitlGraphState, None, HitlGraphState, HitlGraphState]


class HitlRunnerError(Exception):
    """Base error for HITL runner operations."""


class InvalidRunStateError(HitlRunnerError):
    """Run is not in a state that accepts the requested operation."""


class HitlRunner:
    """Coordinates ArtefactStore run rows with the LangGraph HITL stub workflow."""

    def __init__(
        self,
        *,
        graph: HitlCompiledGraph,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._graph = graph
        self._session_factory = session_factory

    def _thread_config(self, run_id: UUID) -> RunnableConfig:
        return {
            "configurable": {
                "thread_id": str(run_id),
                CONFIGURABLE_SESSION_FACTORY: self._session_factory,
            }
        }

    async def start_run(self, request: CreateRunApiRequest) -> RunDetail:
        """Create a run, invoke the graph to the first HITL interrupt, return detail."""
        async with self._session_factory() as session:
            store = PostgresArtefactStore(session)
            run = await store.create_run(
                CreateWorkflowRunRequest(
                    title=request.title,
                    created_by=request.created_by,
                    metadata=request.metadata,
                )
            )
            await store.update_run_status(run.run_id, RunStatus.RUNNING, actor=request.created_by)

        seed: dict[str, Any] | None = None
        if request.business_requirement is not None:
            seed = request.business_requirement.model_dump(mode="json")

        initial: HitlGraphState = {
            "run_id": str(run.run_id),
            "title": request.title,
            "created_by": request.created_by,
            "seed_payload": seed,
            "feedback": None,
            "artefact_id": None,
            "artefact_version": None,
            "artefact_type": None,
            "decision": None,
        }
        await self._graph.ainvoke(initial, config=self._thread_config(run.run_id))
        return await self._sync_and_detail(run.run_id)

    async def get_run_detail(self, run_id: UUID) -> RunDetail:
        async with self._session_factory() as session:
            store = PostgresArtefactStore(session)
            run = await store.get_run(run_id)
        return await self._build_detail(run)

    async def apply_review(self, run_id: UUID, decision: ReviewDecisionRequest) -> RunDetail:
        """Resume a waiting run with Approve / Reject / Request revisions."""
        async with self._session_factory() as session:
            store = PostgresArtefactStore(session)
            run = await store.get_run(run_id)
            if run.status != RunStatus.WAITING_FOR_REVIEW:
                raise InvalidRunStateError(
                    f"Run {run_id} is {run.status.value}, expected waiting_for_review"
                )

            snapshot = await self._graph.aget_state(self._thread_config(run_id))
            values = snapshot.values or {}
            artefact_id = values.get("artefact_id")
            artefact_version = values.get("artefact_version")
            await store.record_review(
                run_id,
                decision=decision.decision.value,
                comments=decision.comments,
                reviewer_id=decision.reviewer_id,
                artefact_id=UUID(artefact_id) if artefact_id else None,
                artefact_version=int(artefact_version) if artefact_version is not None else None,
            )
            await store.update_run_status(
                run_id,
                RunStatus.RUNNING,
                actor=decision.reviewer_id,
                details={"decision": decision.decision.value},
            )

        resume_payload = {
            "decision": decision.decision.value,
            "comments": decision.comments,
            "reviewer_id": decision.reviewer_id,
        }
        await self._graph.ainvoke(
            Command(resume=resume_payload),
            config=self._thread_config(run_id),
        )
        return await self._sync_and_detail(run_id)

    async def _sync_and_detail(self, run_id: UUID) -> RunDetail:
        """Map graph checkpoint / next nodes onto application run status, then return detail."""
        snapshot = await self._graph.aget_state(self._thread_config(run_id))
        next_nodes = tuple(snapshot.next or ())
        values = snapshot.values or {}

        if "await_review" in next_nodes:
            target = RunStatus.WAITING_FOR_REVIEW
        elif not next_nodes:
            decision = values.get("decision")
            if decision == ReviewDecisionKind.REJECT:
                target = RunStatus.TERMINATED
            elif decision == ReviewDecisionKind.APPROVE:
                target = RunStatus.APPROVED
            else:
                target = RunStatus.FAILED
        else:
            target = RunStatus.RUNNING

        async with self._session_factory() as session:
            store = PostgresArtefactStore(session)
            run = await store.get_run(run_id)
            if run.status != target:
                run = await store.update_run_status(run_id, target)

        return await self._build_detail(run)

    async def _build_detail(self, run: WorkflowRun) -> RunDetail:
        pending: PendingReview | None = None
        latest: ArtefactRef | None = None

        async with self._session_factory() as session:
            store = PostgresArtefactStore(session)
            refs = await store.list_artefacts_for_run(run.run_id)
            br_refs = [r for r in refs if r.artefact_type == ArtefactType.BUSINESS_REQUIREMENT]
            if br_refs:
                latest = max(br_refs, key=lambda r: r.version)

        if run.status == RunStatus.WAITING_FOR_REVIEW:
            snapshot = await self._graph.aget_state(self._thread_config(run.run_id))
            values = snapshot.values or {}
            artefact_id = values.get("artefact_id")
            artefact_version = values.get("artefact_version")
            artefact_type = values.get("artefact_type") or ArtefactType.BUSINESS_REQUIREMENT
            if artefact_id and artefact_version is not None:
                pending = PendingReview(
                    artefact=ArtefactRef(
                        artefact_id=UUID(str(artefact_id)),
                        artefact_type=ArtefactType(str(artefact_type)),
                        version=int(artefact_version),
                        run_id=run.run_id,
                    ),
                    feedback=values.get("feedback"),
                )
            elif latest is not None:
                pending = PendingReview(artefact=latest, feedback=None)

        return RunDetail(run=run, pending_review=pending, latest_artefact=latest)


def map_runner_error(exc: Exception) -> tuple[int, str]:
    """Map runner/store errors to (HTTP status, detail)."""
    if isinstance(exc, NotFoundError):
        return 404, str(exc)
    if isinstance(exc, ConflictError):
        return 409, str(exc)
    if isinstance(exc, InvalidRunStateError):
        return 409, str(exc)
    if isinstance(exc, (HitlRunnerError, ArtefactStoreError)):
        return 400, str(exc)
    return 500, str(exc)
