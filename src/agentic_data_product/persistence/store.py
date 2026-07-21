"""Artefact store abstraction and PostgreSQL implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agentic_data_product.domain import (
    ArtefactType,
    AuditEvent,
    CanonicalArtefact,
    LineageEdge,
    WorkflowRun,
    WorkflowRunStatus,
    validate_payload,
)
from agentic_data_product.persistence.repositories import UnitOfWork


class ArtefactStore(ABC):
    @abstractmethod
    async def create_run(self, name: str, metadata: dict[str, Any] | None = None) -> WorkflowRun:
        raise NotImplementedError

    @abstractmethod
    async def get_run(self, run_id: UUID) -> WorkflowRun | None:
        raise NotImplementedError

    @abstractmethod
    async def create_artefact(
        self,
        *,
        run_id: UUID,
        artefact_type: ArtefactType,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> CanonicalArtefact:
        raise NotImplementedError

    @abstractmethod
    async def get_artefact(self, artefact_id: UUID) -> CanonicalArtefact | None:
        raise NotImplementedError

    @abstractmethod
    async def list_artefacts_for_run(self, run_id: UUID) -> list[CanonicalArtefact]:
        raise NotImplementedError


class PostgresArtefactStore(ArtefactStore):
    """M1 PostgreSQL-backed artefact store."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    async def _uow(self) -> AsyncIterator[UnitOfWork]:
        async with self._session_factory() as session:
            uow = UnitOfWork(session)
            try:
                yield uow
                await uow.commit()
            except Exception:
                await uow.rollback()
                raise

    async def create_run(self, name: str, metadata: dict[str, Any] | None = None) -> WorkflowRun:
        run = WorkflowRun(
            name=name,
            status=WorkflowRunStatus.CREATED,
            metadata=metadata or {},
        )
        async with self._uow() as uow:
            created = await uow.runs.create(run)
            await uow.audit.create(
                AuditEvent(
                    run_id=created.run_id,
                    event_type="run_created",
                    actor="api",
                    details={"name": created.name},
                )
            )
            return created

    async def get_run(self, run_id: UUID) -> WorkflowRun | None:
        async with self._uow() as uow:
            return await uow.runs.get(run_id)

    async def create_artefact(
        self,
        *,
        run_id: UUID,
        artefact_type: ArtefactType,
        payload: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> CanonicalArtefact:
        async with self._uow() as uow:
            run = await uow.runs.get(run_id)
            if run is None:
                msg = f"workflow run {run_id} not found"
                raise ValueError(msg)

            version = await uow.artefacts.next_version(run_id, artefact_type)
            validated_payload = validate_payload(artefact_type, payload)
            artefact = CanonicalArtefact(
                run_id=run_id,
                artefact_type=artefact_type,
                version=version,
                payload=validated_payload,
                metadata=metadata or {},
                created_at=datetime.now(UTC),
            )
            created = await uow.artefacts.create(artefact)
            await uow.audit.create(
                AuditEvent(
                    run_id=run_id,
                    event_type="artefact_created",
                    actor="api",
                    details={
                        "artefact_id": str(created.artefact_id),
                        "artefact_type": created.artefact_type.value,
                        "version": created.version,
                    },
                )
            )
            await uow.stamp_updated(run_id)
            return created

    async def get_artefact(self, artefact_id: UUID) -> CanonicalArtefact | None:
        async with self._uow() as uow:
            return await uow.artefacts.get(artefact_id)

    async def list_artefacts_for_run(self, run_id: UUID) -> list[CanonicalArtefact]:
        async with self._uow() as uow:
            return await uow.artefacts.list_for_run(run_id)

    async def add_lineage_edge(
        self,
        *,
        run_id: UUID,
        from_artefact_id: UUID,
        to_artefact_id: UUID,
        relation: str = "derived_from",
        metadata: dict[str, Any] | None = None,
    ) -> LineageEdge:
        async with self._uow() as uow:
            edge = LineageEdge(
                run_id=run_id,
                from_artefact_id=from_artefact_id,
                to_artefact_id=to_artefact_id,
                relation=relation,
                metadata=metadata or {},
            )
            created = await uow.lineage.create(edge)
            await uow.audit.create(
                AuditEvent(
                    run_id=run_id,
                    event_type="lineage_edge_created",
                    actor="api",
                    details={
                        "edge_id": str(created.edge_id),
                        "from_artefact_id": str(from_artefact_id),
                        "to_artefact_id": str(to_artefact_id),
                    },
                )
            )
            return created

    async def list_lineage_for_run(self, run_id: UUID) -> list[LineageEdge]:
        async with self._uow() as uow:
            return await uow.lineage.list_for_run(run_id)

    async def list_audit_for_run(self, run_id: UUID) -> list[AuditEvent]:
        async with self._uow() as uow:
            return await uow.audit.list_for_run(run_id)
