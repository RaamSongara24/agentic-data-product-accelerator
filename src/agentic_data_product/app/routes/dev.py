"""Dev-only persistence APIs for M1 validation (not production HITL/run APIs)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.status import HTTP_422_UNPROCESSABLE_CONTENT

from agentic_data_product.domain.artefacts import (
    ArtefactRef,
    CanonicalArtefact,
    GovernanceMetadata,
    SourceRef,
    validate_artefact_payload,
)
from agentic_data_product.domain.audit import AuditEvent
from agentic_data_product.domain.enums import ArtefactType
from agentic_data_product.domain.lineage import CreateLineageEdgeRequest, LineageEdge
from agentic_data_product.domain.run import CreateWorkflowRunRequest, WorkflowRun
from agentic_data_product.persistence.db import Database, get_database
from agentic_data_product.persistence.store import (
    ArtefactStore,
    ConflictError,
    NotFoundError,
    PostgresArtefactStore,
)

router = APIRouter(prefix="/dev", tags=["dev-persistence"])

DatabaseDep = Annotated[Database, Depends(get_database)]


class CreateArtefactRequest(BaseModel):
    """Request body for creating a versioned artefact."""

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    artefact_type: ArtefactType
    payload: dict[str, Any]
    version: int | None = Field(default=None, ge=1)
    artefact_id: UUID | None = None
    created_by: str | None = None
    governance_metadata: GovernanceMetadata | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)
    parent_versions: list[ArtefactRef] = Field(default_factory=list)


async def store_dep(database: DatabaseDep) -> AsyncIterator[PostgresArtefactStore]:
    async with database.session() as session:
        yield PostgresArtefactStore(session)


StoreDep = Annotated[ArtefactStore, Depends(store_dep)]
OptionalVersionQuery = Annotated[int | None, Query(ge=1)]
RunIdQuery = Annotated[UUID, Query(description="Workflow run identifier")]


def _map_store_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/runs", response_model=WorkflowRun, status_code=status.HTTP_201_CREATED)
async def create_run(body: CreateWorkflowRunRequest, store: StoreDep) -> WorkflowRun:
    try:
        return await store.create_run(body)
    except (NotFoundError, ConflictError) as exc:
        raise _map_store_error(exc) from exc


@router.get("/runs/{run_id}", response_model=WorkflowRun)
async def get_run(run_id: UUID, store: StoreDep) -> WorkflowRun:
    try:
        return await store.get_run(run_id)
    except NotFoundError as exc:
        raise _map_store_error(exc) from exc


@router.post("/artefacts", response_model=CanonicalArtefact, status_code=status.HTTP_201_CREATED)
async def create_artefact(
    body: CreateArtefactRequest,
    store: StoreDep,
) -> CanonicalArtefact:
    # Validate payload before store I/O so invalid bodies return HTTP 422, not 404.
    try:
        validate_artefact_payload(body.artefact_type, body.payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=HTTP_422_UNPROCESSABLE_CONTENT,
            detail=jsonable_encoder(exc.errors()),
        ) from exc

    try:
        return await store.save_artefact(
            run_id=body.run_id,
            artefact_type=body.artefact_type,
            payload=body.payload,
            version=body.version,
            artefact_id=body.artefact_id,
            created_by=body.created_by,
            governance_metadata=body.governance_metadata,
            source_refs=list(body.source_refs),
            parent_versions=list(body.parent_versions),
            validate_payload=True,
        )
    except (NotFoundError, ConflictError) as exc:
        raise _map_store_error(exc) from exc


@router.get("/artefacts/{artefact_id}", response_model=CanonicalArtefact)
async def get_artefact(
    artefact_id: UUID,
    store: StoreDep,
    version: OptionalVersionQuery = None,
) -> CanonicalArtefact:
    try:
        return await store.get_artefact(artefact_id, version=version)
    except NotFoundError as exc:
        raise _map_store_error(exc) from exc


@router.get("/runs/{run_id}/artefacts", response_model=list[ArtefactRef])
async def list_artefacts(run_id: UUID, store: StoreDep) -> list[ArtefactRef]:
    try:
        return await store.list_artefacts_for_run(run_id)
    except NotFoundError as exc:
        raise _map_store_error(exc) from exc


@router.post("/lineage", response_model=LineageEdge, status_code=status.HTTP_201_CREATED)
async def create_lineage(body: CreateLineageEdgeRequest, store: StoreDep) -> LineageEdge:
    try:
        return await store.create_lineage_edge(body)
    except (NotFoundError, ConflictError) as exc:
        raise _map_store_error(exc) from exc


@router.get("/lineage", response_model=list[LineageEdge])
async def list_lineage(run_id: RunIdQuery, store: StoreDep) -> list[LineageEdge]:
    try:
        return await store.list_lineage_for_run(run_id)
    except NotFoundError as exc:
        raise _map_store_error(exc) from exc


@router.get("/audit", response_model=list[AuditEvent])
async def list_audit(run_id: RunIdQuery, store: StoreDep) -> list[AuditEvent]:
    try:
        return await store.list_audit_for_run(run_id)
    except NotFoundError as exc:
        raise _map_store_error(exc) from exc
