"""Unit tests for health and readiness routes."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "agentic-data-product"
    assert "version" in payload


@pytest.mark.asyncio
async def test_ready_unavailable_without_database(client: AsyncClient) -> None:
    response = await client.get("/ready")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["checks"]["database"]["ok"] is False
