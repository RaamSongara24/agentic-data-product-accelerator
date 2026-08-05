"""Production run lifecycle and HITL review APIs (M2)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from agentic_data_product.domain.review import ReviewDecisionRequest
from agentic_data_product.domain.run import CreateRunApiRequest, RunDetail
from agentic_data_product.orchestration.runner import HitlRunner, map_runner_error
from agentic_data_product.persistence.store import NotFoundError

router = APIRouter(tags=["runs"])


def runner_dep(request: Request) -> HitlRunner:
    runner = getattr(request.app.state, "hitl_runner", None)
    if not isinstance(runner, HitlRunner):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="HITL runner is not initialised",
        )
    return runner


RunnerDep = Annotated[HitlRunner, Depends(runner_dep)]


@router.post("/runs", response_model=RunDetail, status_code=status.HTTP_201_CREATED)
async def create_run(body: CreateRunApiRequest, runner: RunnerDep) -> RunDetail:
    try:
        return await runner.start_run(body)
    except Exception as exc:
        code, detail = map_runner_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc


@router.get("/runs/{run_id}", response_model=RunDetail)
async def get_run(run_id: UUID, runner: RunnerDep) -> RunDetail:
    try:
        return await runner.get_run_detail(run_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        code, detail = map_runner_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc


@router.post("/runs/{run_id}/reviews", response_model=RunDetail)
async def submit_review(
    run_id: UUID,
    body: ReviewDecisionRequest,
    runner: RunnerDep,
) -> RunDetail:
    try:
        return await runner.apply_review(run_id, body)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        code, detail = map_runner_error(exc)
        raise HTTPException(status_code=code, detail=detail) from exc
