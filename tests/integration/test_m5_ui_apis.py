"""Integration tests for M5 production artefact/event APIs and UI happy path."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from agentic_data_product.app.main import create_app
from agentic_data_product.config.settings import get_settings
from agentic_data_product.domain.enums import ReviewDecisionKind, RunStatus
from agentic_data_product.persistence.db import set_database
from agentic_data_product.persistence.migrate import apply_migrations

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
        "All seven canonical artefacts approved via Review Package",
    ],
    "stakeholders": ["data_consultant"],
}


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://adp:adp@localhost:5432/adp",
    )


@pytest.fixture(scope="module")
def postgres_available() -> str:
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
async def client(hitl_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=hitl_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


async def _create_run(client: AsyncClient) -> dict:
    resp = await client.post(
        "/runs",
        json={
            "title": "M5 UI run",
            "created_by": "consultant",
            "business_requirement": GOLDEN_BR_BODY,
            "user_context": {"user_id": "consultant"},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _approve(client: AsyncClient, run_id: str) -> dict:
    resp = await client.post(
        f"/runs/{run_id}/reviews",
        json={
            "decision": ReviewDecisionKind.APPROVE,
            "comments": "ok",
            "reviewer_id": "consultant",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.integration
async def test_config_profile_and_ui_available(client: AsyncClient) -> None:
    profile = await client.get("/config/profile")
    assert profile.status_code == 200
    assert profile.json()["llm_provider"] == "deterministic"

    ui = await client.get("/ui/")
    assert ui.status_code == 200
    assert "Start run" in ui.text


@pytest.mark.integration
async def test_artefacts_and_events_through_approve_path(client: AsyncClient) -> None:
    body = await _create_run(client)
    run_id = body["run"]["run_id"]
    assert body["run"]["status"] == RunStatus.WAITING_FOR_REVIEW

    artefacts = await client.get(f"/runs/{run_id}/artefacts")
    assert artefacts.status_code == 200
    refs = artefacts.json()
    assert any(r["artefact_type"] == "business_requirement" for r in refs)
    assert any(r["artefact_type"] == "technical_requirement" for r in refs)

    pending = body["pending_review"]["artefact"]
    detail = await client.get(
        f"/runs/{run_id}/artefacts/{pending['artefact_id']}?version={pending['version']}"
    )
    assert detail.status_code == 200
    artefact = detail.json()
    assert artefact["artefact_type"] == "technical_requirement"
    assert "summary" in artefact["payload"]

    events = await client.get(f"/runs/{run_id}/events")
    assert events.status_code == 200
    actions = {e["action"] for e in events.json()}
    assert "run_created" in actions
    assert "artefact_created" in actions

    # Approve through all HITL gates
    for _ in range(6):
        status = (await client.get(f"/runs/{run_id}")).json()["run"]["status"]
        if status != RunStatus.WAITING_FOR_REVIEW:
            break
        body = await _approve(client, run_id)

    final = (await client.get(f"/runs/{run_id}")).json()
    assert final["run"]["status"] == RunStatus.APPROVED

    final_events = (await client.get(f"/runs/{run_id}/events")).json()
    assert any(e["action"] == "review_submitted" for e in final_events)
    assert len(final_events) >= 10

    final_refs = (await client.get(f"/runs/{run_id}/artefacts")).json()
    types = {r["artefact_type"] for r in final_refs}
    assert types >= {
        "business_requirement",
        "technical_requirement",
        "semantic_model",
        "data_model",
        "pipeline_specification",
        "metric_definitions",
        "review_package",
    }
