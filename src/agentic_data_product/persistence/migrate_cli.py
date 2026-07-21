"""CLI entrypoint for applying schema migrations."""

from __future__ import annotations

import asyncio
import logging

from agentic_data_product.config import get_settings
from agentic_data_product.observability import configure_logging
from agentic_data_product.persistence.migrations import apply_migrations


def run_migrations_cli() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)
    logger = logging.getLogger(__name__)
    applied = asyncio.run(apply_migrations(settings.database_url))
    if applied:
        logger.info("Applied migrations: %s", ", ".join(applied))
    else:
        logger.info("No pending migrations")
