"""Integration tests for M7 lineage and optional Databricks export APIs."""

from __future__ import annotations

import json
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
            "title": "M7 lineage export",
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


async def _approve_all(client: AsyncClient, run_id: str) -> dict:
    body = (await client.get(f"/runs/{run_id}")).json()
    for _ in range(12):
        if body["run"]["status"] != RunStatus.WAITING_FOR_REVIEW:
            break
        body = await _approve(client, run_id)
    return body


@pytest.mark.integration
async def test_lineage_and_export_after_approval(client: AsyncClient) -> None:
    created = await _create_run(client)
    run_id = created["run"]["run_id"]

    # Export before approval must fail
    early = await client.post(f"/runs/{run_id}/export", json={})
    assert early.status_code == 409, early.text

    final = await _approve_all(client, run_id)
    assert final["run"]["status"] == RunStatus.APPROVED

    lineage = await client.get(f"/runs/{run_id}/lineage")
    assert lineage.status_code == 200
    edges = lineage.json()
    assert len(edges) >= 5
    assert all(e["relationship"] == "derived_from" for e in edges)

    events = await client.get(f"/runs/{run_id}/events")
    assert events.status_code == 200
    actions = {e["action"] for e in events.json()}
    assert "lineage_created" in actions
    assert "review_submitted" in actions

    artefacts = await client.get(f"/runs/{run_id}/artefacts")
    rp_refs = [r for r in artefacts.json() if r["artefact_type"] == "review_package"]
    latest_rp = max(rp_refs, key=lambda r: r["version"])
    rp = await client.get(
        f"/runs/{run_id}/artefacts/{latest_rp['artefact_id']}?version={latest_rp['version']}"
    )
    assert rp.status_code == 200
    assert rp.json()["payload"]["decision_state"] == "approved"

    exported = await client.post(
        f"/runs/{run_id}/export",
        json={
            "workspace_label": "mvp-demo-export",
            "catalog": "main",
            "schema": "sales_dp",
            "include_notebooks": True,
        },
    )
    assert exported.status_code == 200, exported.text
    body = exported.json()
    assert body["platform"] == "databricks"
    assert body["mode"] == "export_stub"
    paths = {a["path"] for a in body["assets"]}
    assert "manifest.json" in paths
    assert any("no" in w.lower() and "deploy" in w.lower() for w in body["warnings"])
    manifest = next(a for a in body["assets"] if a["path"] == "manifest.json")
    assert json.loads(manifest["content"])["deploy"] is False

    ui = await client.get("/ui/")
    assert ui.status_code == 200
    assert "Optional platform export" in ui.text
    assert "Lineage" in ui.text
