"""PostgreSQL checkpointer wiring for LangGraph (ADR 001 / 003)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logger = logging.getLogger(__name__)

CheckpointPool = AsyncConnectionPool[AsyncConnection[dict[str, Any]]]


def psycopg_conninfo(database_url: str) -> str:
    """Convert a SQLAlchemy async URL to a psycopg conninfo string."""
    url = database_url
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url.removeprefix("postgresql+asyncpg://")
    elif url.startswith("postgres+asyncpg://"):
        url = "postgresql://" + url.removeprefix("postgres+asyncpg://")
    return url


async def create_checkpointer_pool(database_url: str) -> CheckpointPool:
    """Open an async psycopg connection pool for the LangGraph checkpointer."""
    conninfo = psycopg_conninfo(database_url)
    pool = AsyncConnectionPool(
        conninfo=conninfo,
        kwargs={
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        },
        open=False,
        min_size=1,
        max_size=10,
    )
    await pool.open()
    logger.info("LangGraph checkpointer connection pool opened")
    return cast(CheckpointPool, pool)


async def close_checkpointer_pool(pool: CheckpointPool) -> None:
    """Close the checkpointer pool."""
    await pool.close()
    logger.info("LangGraph checkpointer connection pool closed")


@asynccontextmanager
async def open_checkpointer(database_url: str) -> AsyncIterator[AsyncPostgresSaver]:
    """Context manager that opens a pooled ``AsyncPostgresSaver`` and runs ``setup()``."""
    pool = await create_checkpointer_pool(database_url)
    try:
        checkpointer = AsyncPostgresSaver(conn=pool)
        await checkpointer.setup()
        yield checkpointer
    finally:
        await close_checkpointer_pool(pool)
