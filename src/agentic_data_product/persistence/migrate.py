"""Lightweight SQL migration runner (no Alembic for M1)."""

from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from agentic_data_product.config import get_settings

logger = logging.getLogger(__name__)

VERSIONS_DIR = Path(__file__).resolve().parent / "migrations" / "versions"
MIGRATION_NAME_RE = re.compile(r"^(\d+)_.+\.sql$")


def list_migration_files() -> list[tuple[str, Path]]:
    """Return ordered (version_id, path) pairs from the versions directory."""
    files: list[tuple[str, Path]] = []
    if not VERSIONS_DIR.is_dir():
        return files
    for path in sorted(VERSIONS_DIR.glob("*.sql")):
        match = MIGRATION_NAME_RE.match(path.name)
        if match is None:
            msg = f"Invalid migration filename (expected NNN_name.sql): {path.name}"
            raise ValueError(msg)
        files.append((match.group(1), path))
    return files


async def ensure_migrations_table(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(64) PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    filename TEXT NOT NULL
                )
                """
            )
        )


async def applied_versions(engine: AsyncEngine) -> set[str]:
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version FROM schema_migrations"))
        return {row[0] for row in result}


def _split_sql_statements(sql: str) -> list[str]:
    """Split a SQL file into executable statements (asyncpg is single-statement)."""
    statements: list[str] = []
    for chunk in sql.split(";"):
        # Drop full-line SQL comments, then trim.
        lines = [
            line
            for line in chunk.splitlines()
            if line.strip() and not line.strip().startswith("--")
        ]
        statement = "\n".join(lines).strip()
        if statement:
            statements.append(statement)
    return statements


async def apply_migrations(database_url: str | None = None) -> list[str]:
    """Apply pending SQL migrations. Returns list of applied version ids."""
    url = database_url or get_settings().database_url
    engine = create_async_engine(url, pool_pre_ping=True)
    applied: list[str] = []
    try:
        await ensure_migrations_table(engine)
        already = await applied_versions(engine)
        for version, path in list_migration_files():
            if version in already:
                logger.info("Skipping already-applied migration %s (%s)", version, path.name)
                continue
            sql = path.read_text(encoding="utf-8")
            statements = _split_sql_statements(sql)
            logger.info(
                "Applying migration %s (%s, %s statements)",
                version,
                path.name,
                len(statements),
            )
            async with engine.begin() as conn:
                for statement in statements:
                    await conn.execute(text(statement))
                await conn.execute(
                    text(
                        "INSERT INTO schema_migrations (version, filename) "
                        "VALUES (:version, :filename)"
                    ),
                    {"version": version, "filename": path.name},
                )
            applied.append(version)
        if not applied:
            logger.info("No pending migrations")
        return applied
    finally:
        await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    applied = asyncio.run(apply_migrations())
    if applied:
        print(f"Applied migrations: {', '.join(applied)}")
    else:
        print("No pending migrations")


if __name__ == "__main__":
    main()
