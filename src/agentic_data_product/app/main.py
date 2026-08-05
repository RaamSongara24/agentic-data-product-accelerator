"""FastAPI application factory, lifespan, and ASGI entrypoint."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agentic_data_product import __version__
from agentic_data_product.app.routes.config import router as config_router
from agentic_data_product.app.routes.dev import router as dev_router
from agentic_data_product.app.routes.health import router as health_router
from agentic_data_product.app.routes.runs import router as runs_router
from agentic_data_product.config import get_settings
from agentic_data_product.observability import configure_logging
from agentic_data_product.orchestration.checkpointer import (
    CheckpointPool,
    close_checkpointer_pool,
    create_checkpointer_pool,
)
from agentic_data_product.orchestration.graph import compile_hitl_graph
from agentic_data_product.orchestration.runner import HitlRunner
from agentic_data_product.persistence.db import Database, set_database

logger = logging.getLogger(__name__)


async def _start_hitl(
    app: FastAPI,
    database: Database,
    database_url: str,
) -> CheckpointPool:
    """Open checkpointer pool, compile graph, attach HitlRunner to app state."""
    pool = await create_checkpointer_pool(database_url)
    checkpointer = AsyncPostgresSaver(conn=pool)
    await checkpointer.setup()
    graph = compile_hitl_graph(checkpointer)
    app.state.checkpoint_pool = pool
    app.state.checkpointer = checkpointer
    app.state.hitl_graph = graph
    app.state.hitl_runner = HitlRunner(
        graph=graph,
        session_factory=database.session_factory,
    )
    logger.info("HITL graph and Postgres checkpointer ready")
    return pool


async def _stop_hitl(app: FastAPI) -> None:
    pool = getattr(app.state, "checkpoint_pool", None)
    app.state.hitl_runner = None
    app.state.hitl_graph = None
    app.state.checkpointer = None
    app.state.checkpoint_pool = None
    if pool is not None:
        await close_checkpointer_pool(pool)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start and stop shared resources.

    Database connectivity is attempted at startup. Failure is logged and does not
    prevent the process from listening — ``/ready`` reports dependency health.
    The HITL checkpointer is started only when the database is reachable.
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
    hitl_started = False
    try:
        await database.connect()
        await _start_hitl(app, database, settings.database_url)
        hitl_started = True
    except OSError as exc:
        logger.warning(
            "Database unavailable at startup (%s); /ready will report unavailable "
            "until connectivity is restored",
            exc,
        )
    except Exception:
        logger.exception(
            "Database/HITL unavailable at startup; /ready will report unavailable until "
            "connectivity is restored"
        )

    logger.info("Application startup complete")
    try:
        yield
    finally:
        logger.info("Shutting down application")
        if hitl_started:
            await _stop_hitl(app)
        await database.disconnect()
        set_database(None)
        logger.info("Application shutdown complete")


def _ui_static_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "ui" / "static"


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
    )
    application.include_router(health_router)
    application.include_router(config_router)
    application.include_router(runs_router)
    application.include_router(dev_router)

    ui_dir = _ui_static_dir()
    if ui_dir.is_dir():
        application.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

        @application.get("/", include_in_schema=False)
        async def root_redirect() -> RedirectResponse:
            return RedirectResponse(url="/ui/")

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
