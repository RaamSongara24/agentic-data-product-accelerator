"""ArtefactStore abstraction and PostgreSQL implementation."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from agentic_data_product.domain.artefacts import (
    ArtefactRef,
    CanonicalArtefact,
    GovernanceMetadata,
    SourceRef,
    validate_artefact_payload,
)
from agentic_data_product.domain.audit import AuditEvent
from agentic_data_product.domain.enums import ArtefactType, AuditAction, RunStatus
from agentic_data_product.domain.lineage import CreateLineageEdgeRequest, LineageEdge
from agentic_data_product.domain.run import CreateWorkflowRunRequest, WorkflowRun
from agentic_data_product.persistence.models import (
    ArtefactRow,
    AuditEventRow,
    LineageEdgeRow,
    WorkflowRunRow,
)

logger = logging.getLogger(__name__)


class ArtefactStoreError(Exception):
    """Base error for ArtefactStore operations."""


class NotFoundError(ArtefactStoreError):
    """Requested entity was not found."""


class ConflictError(ArtefactStoreError):
    """Unique constraint or conflicting state."""


def _as_str(value: ArtefactType | AuditAction | RunStatus | str) -> str:
    """Normalize enum-or-str to a plain ``str`` for VARCHAR columns.

    ``StrEnum`` members are also ``str``, so check ``Enum`` first — returning the
    member itself leaves a non-plain value that asyncpg may not bind correctly.
    """
    if isinstance(value, Enum):
        return str(value.value)
    return value


def _utcnow() -> datetime:
    return datetime.now(UTC)


class ArtefactStore(ABC):
    """Persistence interface for runs, versioned artefacts, audit, and lineage."""

    @abstractmethod
    async def create_run(self, request: CreateWorkflowRunRequest) -> WorkflowRun:
        """Create a workflow run and emit a ``run_created`` audit event."""

    @abstractmethod
    async def get_run(self, run_id: UUID) -> WorkflowRun:
        """Return a run by id."""

    @abstractmethod
    async def update_run_status(
        self,
        run_id: UUID,
        status: RunStatus | str,
        *,
        actor: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        """Update run status and emit a ``run_status_updated`` audit event."""

    @abstractmethod
    async def record_review(
        self,
        run_id: UUID,
        *,
        decision: str,
        comments: str = "",
        reviewer_id: str | None = None,
        artefact_id: UUID | None = None,
        artefact_version: int | None = None,
    ) -> AuditEvent:
        """Append a ``review_submitted`` audit event (does not change run status)."""

    @abstractmethod
    async def save_artefact(
        self,
        *,
        run_id: UUID,
        artefact_type: ArtefactType | str,
        payload: dict[str, Any],
        version: int | None = None,
        artefact_id: UUID | None = None,
        created_by: str | None = None,
        governance_metadata: GovernanceMetadata | dict[str, Any] | None = None,
        source_refs: list[SourceRef | dict[str, Any]] | None = None,
        parent_versions: list[ArtefactRef | dict[str, Any]] | None = None,
        validate_payload: bool = True,
    ) -> CanonicalArtefact:
        """Persist a new artefact version (auto-increments when ``version`` is omitted)."""

    @abstractmethod
    async def get_artefact(
        self,
        artefact_id: UUID,
        version: int | None = None,
    ) -> CanonicalArtefact:
        """Return an artefact; latest version when ``version`` is omitted."""

    @abstractmethod
    async def list_artefacts_for_run(self, run_id: UUID) -> list[ArtefactRef]:
        """List artefact refs for a run (all versions)."""

    @abstractmethod
    async def create_lineage_edge(self, request: CreateLineageEdgeRequest) -> LineageEdge:
        """Create a lineage edge and emit a ``lineage_created`` audit event."""

    @abstractmethod
    async def list_lineage_for_run(self, run_id: UUID) -> list[LineageEdge]:
        """List lineage edges for a run."""

    @abstractmethod
    async def list_audit_for_run(self, run_id: UUID) -> list[AuditEvent]:
        """List audit events for a run (oldest first)."""


class PostgresArtefactStore(ArtefactStore):
    """PostgreSQL-backed ArtefactStore using async SQLAlchemy sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_run(self, request: CreateWorkflowRunRequest) -> WorkflowRun:
        now = _utcnow()
        run_id = request.run_id or uuid4()
        row = WorkflowRunRow(
            run_id=run_id,
            status=_as_str(RunStatus.CREATED),
            title=request.title,
            created_by=request.created_by,
            metadata_json=request.metadata,
            created_at=now,
            updated_at=now,
        )
        self._session.add(row)
        try:
            await self._session.flush()
            await self._append_audit(
                run_id=run_id,
                action=AuditAction.RUN_CREATED,
                entity_type="workflow_run",
                entity_id=str(run_id),
                details={"title": request.title},
                actor=request.created_by,
                created_at=now,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ConflictError(f"Run already exists: {run_id}") from exc
        await self._session.refresh(row)
        return self._run_from_row(row)

    async def get_run(self, run_id: UUID) -> WorkflowRun:
        row = await self._session.get(WorkflowRunRow, run_id)
        if row is None:
            raise NotFoundError(f"Run not found: {run_id}")
        return self._run_from_row(row)

    async def update_run_status(
        self,
        run_id: UUID,
        status: RunStatus | str,
        *,
        actor: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        row = await self._session.get(WorkflowRunRow, run_id)
        if row is None:
            raise NotFoundError(f"Run not found: {run_id}")
        previous = row.status
        now = _utcnow()
        new_status = _as_str(RunStatus(status) if not isinstance(status, RunStatus) else status)
        row.status = new_status
        row.updated_at = now
        await self._session.flush()
        await self._append_audit(
            run_id=run_id,
            action=AuditAction.RUN_STATUS_UPDATED,
            entity_type="workflow_run",
            entity_id=str(run_id),
            details={
                "previous_status": previous,
                "status": new_status,
                **(details or {}),
            },
            actor=actor,
            created_at=now,
        )
        await self._session.commit()
        await self._session.refresh(row)
        return self._run_from_row(row)

    async def record_review(
        self,
        run_id: UUID,
        *,
        decision: str,
        comments: str = "",
        reviewer_id: str | None = None,
        artefact_id: UUID | None = None,
        artefact_version: int | None = None,
    ) -> AuditEvent:
        await self.get_run(run_id)
        now = _utcnow()
        event_id = uuid4()
        details: dict[str, Any] = {
            "decision": decision,
            "comments": comments,
        }
        if artefact_id is not None:
            details["artefact_id"] = str(artefact_id)
        if artefact_version is not None:
            details["artefact_version"] = artefact_version
        self._session.add(
            AuditEventRow(
                event_id=event_id,
                run_id=run_id,
                action=_as_str(AuditAction.REVIEW_SUBMITTED),
                entity_type="review",
                entity_id=str(run_id),
                details=details,
                actor=reviewer_id,
                created_at=now,
            )
        )
        await self._session.commit()
        events = await self.list_audit_for_run(run_id)
        for event in reversed(events):
            if event.event_id == event_id:
                return event
        raise ArtefactStoreError(f"Failed to load review audit event {event_id}")

    async def save_artefact(
        self,
        *,
        run_id: UUID,
        artefact_type: ArtefactType | str,
        payload: dict[str, Any],
        version: int | None = None,
        artefact_id: UUID | None = None,
        created_by: str | None = None,
        governance_metadata: GovernanceMetadata | dict[str, Any] | None = None,
        source_refs: list[SourceRef | dict[str, Any]] | None = None,
        parent_versions: list[ArtefactRef | dict[str, Any]] | None = None,
        validate_payload: bool = True,
    ) -> CanonicalArtefact:
        await self.get_run(run_id)
        kind = ArtefactType(artefact_type)
        kind_str = _as_str(kind)

        if validate_payload:
            validated = validate_artefact_payload(kind, payload)
            payload_data = validated.model_dump(mode="json")
        else:
            payload_data = payload

        if version is None:
            version = await self._next_version(run_id, kind_str)

        resolved_artefact_id = artefact_id or await self._artefact_id_for_type(run_id, kind_str)
        gov = self._coerce_governance(governance_metadata)
        refs = self._coerce_source_refs(source_refs)
        parents = self._coerce_parent_versions(parent_versions)
        now = _utcnow()

        row = ArtefactRow(
            artefact_id=resolved_artefact_id,
            run_id=run_id,
            artefact_type=kind_str,
            version=version,
            payload=payload_data,
            created_by=created_by,
            governance_metadata=gov.model_dump(mode="json") if gov else None,
            source_refs=[r.model_dump(mode="json") for r in refs],
            parent_versions=[p.model_dump(mode="json") for p in parents],
            created_at=now,
        )
        self._session.add(row)
        try:
            await self._session.flush()
            await self._append_audit(
                run_id=run_id,
                action=AuditAction.ARTEFACT_CREATED,
                entity_type="artefact",
                entity_id=f"{resolved_artefact_id}:v{version}",
                details={
                    "artefact_id": str(resolved_artefact_id),
                    "artefact_type": kind_str,
                    "version": version,
                },
                actor=created_by,
                created_at=now,
            )
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ConflictError(
                f"Artefact version conflict for run={run_id} type={kind_str} version={version}"
            ) from exc
        await self._session.refresh(row)
        return self._artefact_from_row(row)

    async def get_artefact(
        self,
        artefact_id: UUID,
        version: int | None = None,
    ) -> CanonicalArtefact:
        stmt = select(ArtefactRow).where(ArtefactRow.artefact_id == artefact_id)
        if version is not None:
            stmt = stmt.where(ArtefactRow.version == version)
        else:
            stmt = stmt.order_by(ArtefactRow.version.desc()).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            raise NotFoundError(
                f"Artefact not found: {artefact_id}"
                + (f" version={version}" if version is not None else "")
            )
        return self._artefact_from_row(row)

    async def list_artefacts_for_run(self, run_id: UUID) -> list[ArtefactRef]:
        await self.get_run(run_id)
        stmt = (
            select(ArtefactRow)
            .where(ArtefactRow.run_id == run_id)
            .order_by(ArtefactRow.artefact_type, ArtefactRow.version)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return [
            ArtefactRef(
                artefact_id=row.artefact_id,
                artefact_type=ArtefactType(row.artefact_type),
                version=row.version,
                run_id=row.run_id,
            )
            for row in rows
        ]

    async def create_lineage_edge(self, request: CreateLineageEdgeRequest) -> LineageEdge:
        await self.get_run(request.run_id)
        now = _utcnow()
        edge_id = uuid4()
        row = LineageEdgeRow(
            edge_id=edge_id,
            run_id=request.run_id,
            from_artefact_id=request.from_artefact_id,
            from_version=request.from_version,
            to_artefact_id=request.to_artefact_id,
            to_version=request.to_version,
            relationship=request.relationship,
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        await self._append_audit(
            run_id=request.run_id,
            action=AuditAction.LINEAGE_CREATED,
            entity_type="lineage_edge",
            entity_id=str(edge_id),
            details={
                "from_artefact_id": str(request.from_artefact_id),
                "from_version": request.from_version,
                "to_artefact_id": str(request.to_artefact_id),
                "to_version": request.to_version,
                "relationship": request.relationship,
            },
            actor=None,
            created_at=now,
        )
        await self._session.commit()
        await self._session.refresh(row)
        return self._lineage_from_row(row)

    async def list_lineage_for_run(self, run_id: UUID) -> list[LineageEdge]:
        await self.get_run(run_id)
        stmt = (
            select(LineageEdgeRow)
            .where(LineageEdgeRow.run_id == run_id)
            .order_by(LineageEdgeRow.created_at)
        )
        result = await self._session.execute(stmt)
        return [self._lineage_from_row(row) for row in result.scalars().all()]

    async def list_audit_for_run(self, run_id: UUID) -> list[AuditEvent]:
        await self.get_run(run_id)
        stmt = (
            select(AuditEventRow)
            .where(AuditEventRow.run_id == run_id)
            .order_by(AuditEventRow.created_at)
        )
        result = await self._session.execute(stmt)
        return [self._audit_from_row(row) for row in result.scalars().all()]

    async def _next_version(self, run_id: UUID, artefact_type: str) -> int:
        stmt = (
            select(ArtefactRow.version)
            .where(
                ArtefactRow.run_id == run_id,
                ArtefactRow.artefact_type == artefact_type,
            )
            .order_by(ArtefactRow.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        current = result.scalar_one_or_none()
        return 1 if current is None else int(current) + 1

    async def _artefact_id_for_type(self, run_id: UUID, artefact_type: str) -> UUID:
        """Reuse artefact_id across versions of the same type within a run."""
        stmt = (
            select(ArtefactRow.artefact_id)
            .where(
                ArtefactRow.run_id == run_id,
                ArtefactRow.artefact_type == artefact_type,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()
        return existing if existing is not None else uuid4()

    async def _append_audit(
        self,
        *,
        run_id: UUID,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        details: dict[str, Any],
        actor: str | None,
        created_at: datetime,
    ) -> None:
        self._session.add(
            AuditEventRow(
                event_id=uuid4(),
                run_id=run_id,
                action=_as_str(action),
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                actor=actor,
                created_at=created_at,
            )
        )

    @staticmethod
    def _coerce_governance(
        value: GovernanceMetadata | dict[str, Any] | None,
    ) -> GovernanceMetadata | None:
        if value is None:
            return None
        if isinstance(value, GovernanceMetadata):
            return value
        return GovernanceMetadata.model_validate(value)

    @staticmethod
    def _coerce_source_refs(
        values: list[SourceRef | dict[str, Any]] | None,
    ) -> list[SourceRef]:
        if not values:
            return []
        return [
            item if isinstance(item, SourceRef) else SourceRef.model_validate(item)
            for item in values
        ]

    @staticmethod
    def _coerce_parent_versions(
        values: list[ArtefactRef | dict[str, Any]] | None,
    ) -> list[ArtefactRef]:
        if not values:
            return []
        return [
            item if isinstance(item, ArtefactRef) else ArtefactRef.model_validate(item)
            for item in values
        ]

    @staticmethod
    def _run_from_row(row: WorkflowRunRow) -> WorkflowRun:
        return WorkflowRun(
            run_id=row.run_id,
            status=RunStatus(row.status),
            title=row.title,
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=row.created_by,
            metadata=row.metadata_json or {},
        )

    @staticmethod
    def _artefact_from_row(row: ArtefactRow) -> CanonicalArtefact:
        return CanonicalArtefact(
            artefact_id=row.artefact_id,
            run_id=row.run_id,
            artefact_type=ArtefactType(row.artefact_type),
            version=row.version,
            payload=row.payload,
            created_at=row.created_at,
            created_by=row.created_by,
            governance_metadata=(
                GovernanceMetadata.model_validate(row.governance_metadata)
                if row.governance_metadata
                else None
            ),
            source_refs=[SourceRef.model_validate(item) for item in (row.source_refs or [])],
            parent_versions=[
                ArtefactRef.model_validate(item) for item in (row.parent_versions or [])
            ],
        )

    @staticmethod
    def _lineage_from_row(row: LineageEdgeRow) -> LineageEdge:
        return LineageEdge(
            edge_id=row.edge_id,
            run_id=row.run_id,
            from_artefact_id=row.from_artefact_id,
            from_version=row.from_version,
            to_artefact_id=row.to_artefact_id,
            to_version=row.to_version,
            relationship=row.relationship,
            created_at=row.created_at,
        )

    @staticmethod
    def _audit_from_row(row: AuditEventRow) -> AuditEvent:
        return AuditEvent(
            event_id=row.event_id,
            run_id=row.run_id,
            action=AuditAction(row.action),
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            details=row.details or {},
            created_at=row.created_at,
            actor=row.actor,
        )
