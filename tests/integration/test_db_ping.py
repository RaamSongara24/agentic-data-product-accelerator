"""Integration tests for database connectivity and readiness."""

import pytest
from httpx import AsyncClient

from agentic_data_product.persistence.db import Database


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_ping(postgres_available: str) -> None:
    database = Database(postgres_available)
    await database.connect()
    try:
        assert await database.ping() is True
    finally:
        await database.disconnect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ready_ok(integration_client: AsyncClient) -> None:
    response = await integration_client.get("/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"]["ok"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_health_ok_with_lifespan(integration_client: AsyncClient) -> None:
    response = await integration_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
