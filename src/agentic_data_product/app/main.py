"""FastAPI application factory, lifespan, and ASGI entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from agentic_data_product import __version__
from agentic_data_product.app.routes.dev import router as dev_router
from agentic_data_product.app.routes.health import router as health_router
from agentic_data_product.config import get_settings
from agentic_data_product.observability import configure_logging
from agentic_data_product.persistence.db import Database, set_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start and stop shared resources.

    Database connectivity is attempted at startup. Failure is logged and does not
    prevent the process from listening — ``/ready`` reports dependency health.
    """
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)
    logger.info(
        "Starting %s v%s (env=%s)",
        settings.app_name,
        __version__,
        settings.app_env,
    )

    database = Database(settings.database_url)
    set_database(database)
    app.state.database = database
    try:
        await database.connect()
    except OSError as exc:
        logger.warning(
            "Database unavailable at startup (%s); /ready will report unavailable "
            "until connectivity is restored",
            exc,
        )
    except Exception:
        logger.exception(
            "Database unavailable at startup; /ready will report unavailable until "
            "connectivity is restored"
        )

    logger.info("Application startup complete")
    try:
        yield
    finally:
        logger.info("Shutting down application")
        await database.disconnect()
        set_database(None)
        logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(dev_router)
    return application


app = create_app()


def run() -> None:
    """Console script entrypoint."""
    settings = get_settings()
    uvicorn.run(
        "agentic_data_product.app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_env == "development",
    )
