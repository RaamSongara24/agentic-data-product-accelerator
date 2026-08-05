"""Integration tests for M2 HITL APIs and durable checkpointer resume."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from agentic_data_product.app.main import create_app
from agentic_data_product.config.settings import get_settings
from agentic_data_product.domain.enums import ReviewDecisionKind, RunStatus
from agentic_data_product.persistence.db import set_database
from agentic_data_product.persistence.migrate import apply_migrations


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://adp:adp@localhost:5432/adp",
    )


@pytest.fixture(scope="module")
def postgres_available() -> str:
    """Skip when PostgreSQL is unreachable; apply app migrations when available."""
    import asyncio

    from agentic_data_product.persistence.db import Database

    url = _database_url()

    async def _probe_and_migrate() -> None:
        db = Database(url)
        await db.connect()
        await db.disconnect()
        await apply_migrations(url)

    try:
        asyncio.run(_probe_and_migrate())
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL not available: {exc}")
    return url


@pytest.fixture
async def hitl_app(postgres_available: str) -> AsyncIterator[FastAPI]:
    get_settings.cache_clear()
    os.environ["DATABASE_URL"] = postgres_available
    get_settings.cache_clear()
    application = create_app()
    async with application.router.lifespan_context(application):
        yield application
    get_settings.cache_clear()
    set_database(None)


@pytest.fixture
async def hitl_client(hitl_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=hitl_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.integration
async def test_create_run_reaches_waiting_for_review(hitl_client: AsyncClient) -> None:
    resp = await hitl_client.post(
        "/runs",
        json={"title": "M2 approve path", "created_by": "consultant"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
    assert body["pending_review"] is not None
    assert body["pending_review"]["artefact"]["version"] == 1
    assert body["latest_artefact"]["artefact_type"] == "business_requirement"

    run_id = body["run"]["run_id"]
    get_resp = await hitl_client.get(f"/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["run"]["status"] == RunStatus.WAITING_FOR_REVIEW


@pytest.mark.integration
async def test_approve_completes_run(hitl_client: AsyncClient) -> None:
    created = await hitl_client.post("/runs", json={"title": "approve me"})
    run_id = created.json()["run"]["run_id"]

    reviewed = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={
            "decision": ReviewDecisionKind.APPROVE,
            "comments": "Looks good",
            "reviewer_id": "consultant",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    body = reviewed.json()
    assert body["run"]["status"] == RunStatus.APPROVED
    assert body["pending_review"] is None


@pytest.mark.integration
async def test_reject_terminates_run(hitl_client: AsyncClient) -> None:
    created = await hitl_client.post("/runs", json={"title": "reject me"})
    run_id = created.json()["run"]["run_id"]

    reviewed = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={"decision": ReviewDecisionKind.REJECT, "comments": "Out of scope"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["run"]["status"] == RunStatus.TERMINATED


@pytest.mark.integration
async def test_request_revisions_bumps_version_and_returns_to_interrupt(
    hitl_client: AsyncClient,
) -> None:
    created = await hitl_client.post("/runs", json={"title": "revise me"})
    body = created.json()
    run_id = body["run"]["run_id"]
    v1 = body["pending_review"]["artefact"]["version"]
    assert v1 == 1

    revised = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={
            "decision": ReviewDecisionKind.REQUEST_REVISIONS,
            "comments": "Add clearer success criteria",
            "reviewer_id": "consultant",
        },
    )
    assert revised.status_code == 200, revised.text
    rev_body = revised.json()
    assert rev_body["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
    assert rev_body["pending_review"]["artefact"]["version"] == 2
    assert rev_body["latest_artefact"]["version"] == 2

    # Same artefact_id across versions
    assert (
        rev_body["pending_review"]["artefact"]["artefact_id"]
        == body["pending_review"]["artefact"]["artefact_id"]
    )

    approved = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={"decision": ReviewDecisionKind.APPROVE, "comments": "ok now"},
    )
    assert approved.json()["run"]["status"] == RunStatus.APPROVED


@pytest.mark.integration
async def test_review_while_not_waiting_conflicts(hitl_client: AsyncClient) -> None:
    created = await hitl_client.post("/runs", json={"title": "once"})
    run_id = created.json()["run"]["run_id"]
    await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={"decision": ReviewDecisionKind.APPROVE},
    )
    second = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={"decision": ReviewDecisionKind.APPROVE},
    )
    assert second.status_code == 409


@pytest.mark.integration
async def test_hitl_survives_api_process_restart(postgres_available: str) -> None:
    """Start a run, tear down the ASGI app, create a new app, resume from checkpointer."""
    get_settings.cache_clear()
    os.environ["DATABASE_URL"] = postgres_available
    get_settings.cache_clear()

    app1 = create_app()
    async with app1.router.lifespan_context(app1):
        transport1 = ASGITransport(app=app1)
        async with AsyncClient(transport=transport1, base_url="http://test") as client1:
            created = await client1.post("/runs", json={"title": "durable run"})
            assert created.status_code == 201, created.text
            run_id = UUID(created.json()["run"]["run_id"])
            assert created.json()["run"]["status"] == RunStatus.WAITING_FOR_REVIEW

    # Process "restart": new app instance, same Postgres (checkpoints + artefacts).
    get_settings.cache_clear()
    set_database(None)
    app2 = create_app()
    async with app2.router.lifespan_context(app2):
        transport2 = ASGITransport(app=app2)
        async with AsyncClient(transport=transport2, base_url="http://test") as client2:
            status_resp = await client2.get(f"/runs/{run_id}")
            assert status_resp.status_code == 200
            assert status_resp.json()["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
            assert status_resp.json()["pending_review"]["artefact"]["version"] == 1

            resumed = await client2.post(
                f"/runs/{run_id}/reviews",
                json={
                    "decision": ReviewDecisionKind.REQUEST_REVISIONS,
                    "comments": "resume after restart",
                },
            )
            assert resumed.status_code == 200, resumed.text
            assert resumed.json()["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
            assert resumed.json()["pending_review"]["artefact"]["version"] == 2

            final = await client2.post(
                f"/runs/{run_id}/reviews",
                json={"decision": ReviewDecisionKind.APPROVE},
            )
            assert final.json()["run"]["status"] == RunStatus.APPROVED

    get_settings.cache_clear()
    set_database(None)
