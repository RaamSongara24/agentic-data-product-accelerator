"""Integration fixtures requiring PostgreSQL."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from agentic_data_product.app.main import create_app
from agentic_data_product.config.settings import get_settings
from agentic_data_product.persistence.db import Database, set_database


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://adp:adp@localhost:5432/adp",
    )


@pytest.fixture(scope="module")
def postgres_available() -> str:
    """Skip the module when PostgreSQL is not reachable."""
    import asyncio

    url = _database_url()

    async def _probe() -> None:
        db = Database(url)
        await db.connect()
        await db.disconnect()

    try:
        asyncio.run(_probe())
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL not available: {exc}")
    return url


@pytest.fixture
async def integration_app(postgres_available: str) -> AsyncIterator[FastAPI]:
    get_settings.cache_clear()
    os.environ["DATABASE_URL"] = postgres_available
    get_settings.cache_clear()
    application = create_app()
    # Use real lifespan
    async with application.router.lifespan_context(application):
        yield application
    get_settings.cache_clear()
    set_database(None)


@pytest.fixture
async def integration_client(integration_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=integration_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
