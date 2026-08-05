"""Integration tests for M3 HITL APIs (TR + mapping stages) and durable resume."""

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
from agentic_data_product.integrations.discovery import INACCESSIBLE_OBJECT_IDS
from agentic_data_product.persistence.db import set_database
from agentic_data_product.persistence.migrate import apply_migrations


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://adp:adp@localhost:5432/adp",
    )


GOLDEN_BR_BODY = {
    "title": "Sales analytics data product",
    "intent": (
        "Deliver a governed sales analytics data product covering orders, "
        "customers, and products for consultant-led design."
    ),
    "objectives": [
        "Analyse order amounts and order counts by customer and region",
        "Support product-level sales reporting",
    ],
    "constraints": [
        "Must not use HR or security datasets the consultant cannot access",
        "Outputs must remain technology-agnostic canonical artefacts",
    ],
    "success_criteria": [
        "Technical Requirement approved via HITL",
        "Mapping data-model slice approved via HITL",
    ],
    "stakeholders": ["data_consultant"],
}


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
    os.environ["LLM_PROVIDER"] = "deterministic"
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


async def _create_run(client: AsyncClient, *, title: str = "M3 run") -> dict:
    resp = await client.post(
        "/runs",
        json={
            "title": title,
            "created_by": "consultant",
            "business_requirement": GOLDEN_BR_BODY,
            "user_context": {"user_id": "consultant"},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.mark.integration
async def test_create_run_reaches_tr_waiting_for_review(hitl_client: AsyncClient) -> None:
    body = await _create_run(hitl_client, title="M3 TR gate")
    assert body["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
    assert body["pending_review"] is not None
    assert body["pending_review"]["artefact"]["artefact_type"] == "technical_requirement"
    assert body["pending_review"]["artefact"]["version"] == 1
    assert body["latest_artefact"]["artefact_type"] == "technical_requirement"


@pytest.mark.integration
async def test_approve_through_mapping_stage(
    hitl_client: AsyncClient,
    hitl_app: FastAPI,
) -> None:
    """M3 exit criterion: consultant can approve through mapping via API."""
    created = await _create_run(hitl_client, title="approve through mapping")
    run_id = created["run"]["run_id"]

    tr_approved = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={
            "decision": ReviewDecisionKind.APPROVE,
            "comments": "TR looks good",
            "reviewer_id": "consultant",
        },
    )
    assert tr_approved.status_code == 200, tr_approved.text
    mid = tr_approved.json()
    assert mid["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
    assert mid["pending_review"]["artefact"]["artefact_type"] == "data_model"

    # Inaccessible fixtures must not appear in mapping artefact source refs / context
    from agentic_data_product.orchestration.runner import HitlRunner
    from agentic_data_product.persistence.store import PostgresArtefactStore

    runner: HitlRunner = hitl_app.state.hitl_runner
    detail = await runner.get_run_detail(UUID(run_id))
    assert detail.pending_review is not None
    async with runner._session_factory() as session:
        store = PostgresArtefactStore(session)
        artefact = await store.get_artefact(
            detail.pending_review.artefact.artefact_id,
            detail.pending_review.artefact.version,
        )
    blob = str(artefact.payload) + str([r.model_dump() for r in artefact.source_refs])
    for forbidden in INACCESSIBLE_OBJECT_IDS:
        assert forbidden not in blob

    mapped = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={
            "decision": ReviewDecisionKind.APPROVE,
            "comments": "Mapping approved",
            "reviewer_id": "consultant",
        },
    )
    assert mapped.status_code == 200, mapped.text
    assert mapped.json()["run"]["status"] == RunStatus.APPROVED
    assert mapped.json()["pending_review"] is None


@pytest.mark.integration
async def test_reject_at_tr_terminates_run(hitl_client: AsyncClient) -> None:
    created = await _create_run(hitl_client, title="reject TR")
    run_id = created["run"]["run_id"]

    reviewed = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={"decision": ReviewDecisionKind.REJECT, "comments": "Out of scope"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["run"]["status"] == RunStatus.TERMINATED


@pytest.mark.integration
async def test_request_revisions_on_tr_bumps_version(hitl_client: AsyncClient) -> None:
    created = await _create_run(hitl_client, title="revise TR")
    body = created
    run_id = body["run"]["run_id"]
    v1 = body["pending_review"]["artefact"]["version"]
    assert v1 == 1
    artefact_id = body["pending_review"]["artefact"]["artefact_id"]

    revised = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={
            "decision": ReviewDecisionKind.REQUEST_REVISIONS,
            "comments": "Clarify acceptance criteria grain",
            "reviewer_id": "consultant",
        },
    )
    assert revised.status_code == 200, revised.text
    rev_body = revised.json()
    assert rev_body["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
    assert rev_body["pending_review"]["artefact"]["artefact_type"] == "technical_requirement"
    assert rev_body["pending_review"]["artefact"]["version"] == 2
    assert rev_body["pending_review"]["artefact"]["artefact_id"] == artefact_id


@pytest.mark.integration
async def test_reject_at_mapping_terminates(hitl_client: AsyncClient) -> None:
    created = await _create_run(hitl_client, title="reject mapping")
    run_id = created["run"]["run_id"]
    await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={"decision": ReviewDecisionKind.APPROVE},
    )
    rejected = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={"decision": ReviewDecisionKind.REJECT, "comments": "Bad mapping"},
    )
    assert rejected.json()["run"]["status"] == RunStatus.TERMINATED


@pytest.mark.integration
async def test_review_while_not_waiting_conflicts(hitl_client: AsyncClient) -> None:
    created = await _create_run(hitl_client, title="once")
    run_id = created["run"]["run_id"]
    await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={"decision": ReviewDecisionKind.APPROVE},
    )
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
    os.environ["LLM_PROVIDER"] = "deterministic"
    get_settings.cache_clear()

    app1 = create_app()
    async with app1.router.lifespan_context(app1):
        transport1 = ASGITransport(app=app1)
        async with AsyncClient(transport=transport1, base_url="http://test") as client1:
            created = await client1.post(
                "/runs",
                json={
                    "title": "durable run",
                    "created_by": "consultant",
                    "business_requirement": GOLDEN_BR_BODY,
                    "user_context": {"user_id": "consultant"},
                },
            )
            assert created.status_code == 201, created.text
            run_id = UUID(created.json()["run"]["run_id"])
            assert created.json()["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
            assert (
                created.json()["pending_review"]["artefact"]["artefact_type"]
                == "technical_requirement"
            )

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

            revised = await client2.post(
                f"/runs/{run_id}/reviews",
                json={
                    "decision": ReviewDecisionKind.REQUEST_REVISIONS,
                    "comments": "resume after restart",
                },
            )
            assert revised.status_code == 200, revised.text
            assert revised.json()["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
            assert revised.json()["pending_review"]["artefact"]["version"] == 2

            tr_ok = await client2.post(
                f"/runs/{run_id}/reviews",
                json={"decision": ReviewDecisionKind.APPROVE},
            )
            assert tr_ok.json()["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
            assert tr_ok.json()["pending_review"]["artefact"]["artefact_type"] == "data_model"

            final = await client2.post(
                f"/runs/{run_id}/reviews",
                json={"decision": ReviewDecisionKind.APPROVE},
            )
            assert final.json()["run"]["status"] == RunStatus.APPROVED

    get_settings.cache_clear()
    set_database(None)
