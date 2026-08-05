"""Async SQLAlchemy engine and health ping for PostgreSQL."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger(__name__)


class Database:
    """Thin wrapper around an async SQLAlchemy engine for M0 connectivity."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            msg = "Database engine is not started"
            raise RuntimeError(msg)
        return self._engine

    async def connect(self) -> None:
        """Create the async engine and verify connectivity.

        The engine is retained even if the initial ping fails so readiness
        checks can retry without recreating configuration.
        """
        if self._engine is None:
            logger.info("Creating database engine")
            self._engine = create_async_engine(
                self._database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=5,
            )
            self._session_factory = async_sessionmaker(
                self._engine,
                expire_on_commit=False,
                class_=AsyncSession,
            )
        await self.ping()
        logger.info("Database connection verified")

    async def disconnect(self) -> None:
        """Dispose the engine."""
        if self._engine is None:
            return
        logger.info("Disposing database engine")
        await self._engine.dispose()
        self._engine = None
        self._session_factory = None

    async def ping(self) -> bool:
        """Return True when ``SELECT 1`` succeeds."""
        async with self.engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            value = result.scalar_one()
            return bool(value == 1)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a short-lived async session (reserved for later milestones)."""
        if self._session_factory is None:
            msg = "Database session factory is not started"
            raise RuntimeError(msg)
        async with self._session_factory() as session:
            yield session


_database: Database | None = None


def get_database() -> Database:
    """Return the process-wide Database instance."""
    if _database is None:
        msg = "Database has not been initialised"
        raise RuntimeError(msg)
    return _database


def set_database(database: Database | None) -> None:
    """Set or clear the process-wide Database instance (used by lifespan)."""
    global _database
    _database = database
