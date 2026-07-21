"""Repository layer for M1 persistence objects."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_data_product.domain import (
    ArtefactType,
    AuditEvent,
    CanonicalArtefact,
    LineageEdge,
    WorkflowRun,
    WorkflowRunStatus,
)
from agentic_data_product.persistence.models import (
    ArtefactORM,
    AuditEventORM,
    LineageEdgeORM,
    WorkflowRunORM,
)


def _to_workflow_run(model: WorkflowRunORM) -> WorkflowRun:
    return WorkflowRun(
        run_id=model.run_id,
        name=model.name,
        status=WorkflowRunStatus(model.status),
        metadata=model.metadata_json,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_artefact(model: ArtefactORM) -> CanonicalArtefact:
    return CanonicalArtefact(
        artefact_id=model.artefact_id,
        run_id=model.run_id,
        artefact_type=ArtefactType(model.artefact_type),
        version=model.version,
        payload=model.payload,
        metadata=model.metadata_json,
        created_at=model.created_at,
    )


def _to_audit_event(model: AuditEventORM) -> AuditEvent:
    return AuditEvent(
        event_id=model.event_id,
        run_id=model.run_id,
        event_type=model.event_type,
        actor=model.actor,
        details=model.details,
        created_at=model.created_at,
    )


def _to_lineage(model: LineageEdgeORM) -> LineageEdge:
    return LineageEdge(
        edge_id=model.edge_id,
        run_id=model.run_id,
        from_artefact_id=model.from_artefact_id,
        to_artefact_id=model.to_artefact_id,
        relation=model.relation,
        metadata=model.metadata_json,
        created_at=model.created_at,
    )


class WorkflowRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, run: WorkflowRun) -> WorkflowRun:
        model = WorkflowRunORM(
            run_id=run.run_id,
            name=run.name,
            status=run.status.value,
            metadata_json=run.metadata,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_workflow_run(model)

    async def get(self, run_id: UUID) -> WorkflowRun | None:
        model = await self._session.get(WorkflowRunORM, run_id)
        if model is None:
            return None
        return _to_workflow_run(model)


class ArtefactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, artefact: CanonicalArtefact) -> CanonicalArtefact:
        model = ArtefactORM(
            artefact_id=artefact.artefact_id,
            run_id=artefact.run_id,
            artefact_type=artefact.artefact_type.value,
            version=artefact.version,
            payload=artefact.payload,
            metadata_json=artefact.metadata,
            created_at=artefact.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_artefact(model)

    async def get(self, artefact_id: UUID) -> CanonicalArtefact | None:
        model = await self._session.get(ArtefactORM, artefact_id)
        if model is None:
            return None
        return _to_artefact(model)

    async def list_for_run(self, run_id: UUID) -> list[CanonicalArtefact]:
        stmt = (
            select(ArtefactORM)
            .where(ArtefactORM.run_id == run_id)
            .order_by(ArtefactORM.created_at.asc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_artefact(m) for m in models]

    async def next_version(self, run_id: UUID, artefact_type: ArtefactType) -> int:
        stmt = select(ArtefactORM).where(
            ArtefactORM.run_id == run_id,
            ArtefactORM.artefact_type == artefact_type.value,
        )
        models = (await self._session.execute(stmt)).scalars().all()
        if not models:
            return 1
        return max(m.version for m in models) + 1


class AuditEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: AuditEvent) -> AuditEvent:
        model = AuditEventORM(
            event_id=event.event_id,
            run_id=event.run_id,
            event_type=event.event_type,
            actor=event.actor,
            details=event.details,
            created_at=event.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_audit_event(model)

    async def list_for_run(self, run_id: UUID) -> list[AuditEvent]:
        stmt = (
            select(AuditEventORM)
            .where(AuditEventORM.run_id == run_id)
            .order_by(AuditEventORM.created_at.asc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_audit_event(m) for m in models]


class LineageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, edge: LineageEdge) -> LineageEdge:
        model = LineageEdgeORM(
            edge_id=edge.edge_id,
            run_id=edge.run_id,
            from_artefact_id=edge.from_artefact_id,
            to_artefact_id=edge.to_artefact_id,
            relation=edge.relation,
            metadata_json=edge.metadata,
            created_at=edge.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_lineage(model)

    async def list_for_run(self, run_id: UUID) -> list[LineageEdge]:
        stmt = (
            select(LineageEdgeORM)
            .where(LineageEdgeORM.run_id == run_id)
            .order_by(LineageEdgeORM.created_at.asc())
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [_to_lineage(m) for m in models]


class UnitOfWork:
    """Lightweight unit-of-work wrapper for repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = WorkflowRunRepository(session)
        self.artefacts = ArtefactRepository(session)
        self.audit = AuditEventRepository(session)
        self.lineage = LineageRepository(session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def stamp_updated(self, run_id: UUID) -> None:
        model = await self.session.get(WorkflowRunORM, run_id)
        if model is not None:
            model.updated_at = datetime.now(UTC)
