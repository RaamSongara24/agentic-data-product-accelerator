"""Liveness and readiness endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from agentic_data_product import __version__
from agentic_data_product.persistence.db import get_database

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = Field(description="Process liveness status")
    version: str
    service: str


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — process is up (does not check dependencies)."""
    return HealthResponse(
        status="ok",
        version=__version__,
        service="agentic-data-product",
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready(response: Response) -> ReadyResponse:
    """Readiness probe — PostgreSQL must be reachable."""
    checks: dict[str, Any] = {}
    try:
        database = get_database()
        ok = await database.ping()
        checks["database"] = {"ok": ok}
    except Exception as exc:  # noqa: BLE001 — surface any connectivity failure
        logger.warning("Readiness check failed: %s", exc)
        checks["database"] = {"ok": False, "error": str(exc)}
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(status="unavailable", checks=checks)

    if not checks["database"]["ok"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(status="unavailable", checks=checks)

    return ReadyResponse(status="ready", checks=checks)
