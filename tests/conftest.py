"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from agentic_data_product.app.main import create_app
from agentic_data_product.config.settings import get_settings
from agentic_data_product.observability import configure_logging
from agentic_data_product.persistence.db import set_database


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Reset settings cache around each test."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("LOG_JSON", "false")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
    set_database(None)


@pytest.fixture
def app(settings: None) -> FastAPI:
    """Application with a no-op lifespan (no database) for unit tests."""
    application = create_app()

    @asynccontextmanager
    async def test_lifespan(_app: FastAPI) -> AsyncIterator[None]:
        configure_logging(level="WARNING", json_logs=False)
        set_database(None)
        yield

    application.router.lifespan_context = test_lifespan
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
