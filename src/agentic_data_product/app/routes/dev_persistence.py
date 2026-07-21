"""Development-only persistence endpoints for Milestone M1."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ValidationError

from agentic_data_product.app.dependencies import artefact_store_dep
from agentic_data_product.domain import ArtefactType
from agentic_data_product.persistence import PostgresArtefactStore

router = APIRouter(prefix="/dev", tags=["dev-persistence"])


class CreateRunRequest(BaseModel):
    name: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateArtefactRequest(BaseModel):
    run_id: UUID
    artefact_type: ArtefactType
    payload: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateLineageRequest(BaseModel):
    run_id: UUID
    from_artefact_id: UUID
    to_artefact_id: UUID
    relation: str = "derived_from"
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def create_run(
    body: CreateRunRequest,
    store: PostgresArtefactStore = Depends(artefact_store_dep),
) -> dict[str, Any]:
    run = await store.create_run(name=body.name, metadata=body.metadata)
    return run.model_dump(mode="json")


@router.get("/runs/{run_id}")
async def get_run(
    run_id: UUID,
    store: PostgresArtefactStore = Depends(artefact_store_dep),
) -> dict[str, Any]:
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="run not found")
    return run.model_dump(mode="json")


@router.post("/artefacts", status_code=status.HTTP_201_CREATED)
async def create_artefact(
    body: CreateArtefactRequest,
    store: PostgresArtefactStore = Depends(artefact_store_dep),
) -> dict[str, Any]:
    try:
        artefact = await store.create_artefact(
            run_id=body.run_id,
            artefact_type=body.artefact_type,
            payload=body.payload,
            metadata=body.metadata,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.errors()
        ) from exc
    return artefact.model_dump(mode="json")


@router.get("/artefacts/{artefact_id}")
async def get_artefact(
    artefact_id: UUID,
    store: PostgresArtefactStore = Depends(artefact_store_dep),
) -> dict[str, Any]:
    artefact = await store.get_artefact(artefact_id)
    if artefact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="artefact not found")
    return artefact.model_dump(mode="json")


@router.get("/artefacts")
async def list_artefacts(
    run_id: UUID = Query(...),
    store: PostgresArtefactStore = Depends(artefact_store_dep),
) -> list[dict[str, Any]]:
    artefacts = await store.list_artefacts_for_run(run_id)
    return [a.model_dump(mode="json") for a in artefacts]


@router.post("/lineage", status_code=status.HTTP_201_CREATED)
async def create_lineage(
    body: CreateLineageRequest,
    store: PostgresArtefactStore = Depends(artefact_store_dep),
) -> dict[str, Any]:
    edge = await store.add_lineage_edge(
        run_id=body.run_id,
        from_artefact_id=body.from_artefact_id,
        to_artefact_id=body.to_artefact_id,
        relation=body.relation,
        metadata=body.metadata,
    )
    return edge.model_dump(mode="json")


@router.get("/lineage")
async def list_lineage(
    run_id: UUID = Query(...),
    store: PostgresArtefactStore = Depends(artefact_store_dep),
) -> list[dict[str, Any]]:
    edges = await store.list_lineage_for_run(run_id)
    return [edge.model_dump(mode="json") for edge in edges]


@router.get("/audit")
async def list_audit(
    run_id: UUID = Query(...),
    store: PostgresArtefactStore = Depends(artefact_store_dep),
) -> list[dict[str, Any]]:
    events = await store.list_audit_for_run(run_id)
    return [event.model_dump(mode="json") for event in events]
