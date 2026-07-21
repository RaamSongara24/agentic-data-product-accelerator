"""Lightweight migration framework for M1.

This is intentionally minimal and equivalent to a migration tool for early
project stages: versioned migration records plus deterministic schema creation.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from agentic_data_product.persistence.models import Base

MIGRATION_TABLE = "schema_migrations"


@dataclass(frozen=True)
class Migration:
    version: str
    description: str

    async def apply(self, engine: AsyncEngine) -> None:
        """Apply this migration."""
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(
                text(
                    f"""
                    INSERT INTO {MIGRATION_TABLE} (version, description)
                    VALUES (:version, :description)
                    ON CONFLICT (version) DO NOTHING
                    """
                ),
                {"version": self.version, "description": self.description},
            )


MIGRATIONS: tuple[Migration, ...] = (
    Migration(version="20260721_0001", description="M1 initial schema"),
)


async def ensure_migration_table(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                    version VARCHAR(64) PRIMARY KEY,
                    description VARCHAR(255) NOT NULL,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )


async def get_applied_versions(engine: AsyncEngine) -> set[str]:
    async with engine.begin() as connection:
        result = await connection.execute(text(f"SELECT version FROM {MIGRATION_TABLE}"))
        return {str(row[0]) for row in result.fetchall()}


async def apply_migrations(database_url: str) -> list[str]:
    """Apply all pending migrations and return applied versions."""
    engine = create_async_engine(database_url, pool_pre_ping=True)
    try:
        await ensure_migration_table(engine)
        applied = await get_applied_versions(engine)
        executed: list[str] = []
        for migration in MIGRATIONS:
            if migration.version in applied:
                continue
            await migration.apply(engine)
            executed.append(migration.version)
        return executed
    finally:
        await engine.dispose()
