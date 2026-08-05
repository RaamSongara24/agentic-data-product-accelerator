"""Load smoke: two concurrent HITL runs with separate checkpointer thread_ids."""

from __future__ import annotations

import asyncio
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

GOLDEN_BR_A = {
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

GOLDEN_BR_B = {
    "title": "Customer retention analytics",
    "intent": (
        "Design a governed customer retention analytics product using only "
        "accessible sales and customer datasets."
    ),
    "objectives": [
        "Track repeat order rates by customer segment and region",
        "Support churn risk reporting for sales consultants",
    ],
    "constraints": [
        "Must not use HR payroll or security audit datasets",
        "Canonical artefacts only — no vendor DSL in agent outputs",
    ],
    "success_criteria": [
        "Approved Technical Requirement and mapping slice",
        "Approved Review Package covering seven artefacts",
    ],
    "stakeholders": ["data_consultant", "sales_ops"],
}


def _database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://adp:adp@localhost:5432/adp",
    )


@pytest.fixture(scope="module")
def postgres_available() -> str:
    import asyncio as _asyncio

    from agentic_data_product.persistence.db import Database

    url = _database_url()

    async def _probe_and_migrate() -> None:
        db = Database(url)
        await db.connect()
        await db.disconnect()
        await apply_migrations(url)

    try:
        _asyncio.run(_probe_and_migrate())
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


async def _create_run(client: AsyncClient, *, title: str, br: dict) -> dict:
    resp = await client.post(
        "/runs",
        json={
            "title": title,
            "created_by": "consultant",
            "business_requirement": br,
            "user_context": {"user_id": "consultant"},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _approve_to_completion(client: AsyncClient, run_id: str) -> dict:
    body = (await client.get(f"/runs/{run_id}")).json()
    for _ in range(12):
        status = body["run"]["status"]
        if status == RunStatus.APPROVED:
            return body
        if status != RunStatus.WAITING_FOR_REVIEW:
            raise AssertionError(f"Unexpected status {status!r}: {body}")
        resp = await client.post(
            f"/runs/{run_id}/reviews",
            json={
                "decision": ReviewDecisionKind.APPROVE,
                "comments": "concurrent smoke approve",
                "reviewer_id": "consultant",
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
    raise AssertionError(f"Run {run_id} did not reach approved: {body}")


@pytest.mark.integration
async def test_two_concurrent_runs_separate_checkpointer_threads(
    hitl_client: AsyncClient,
) -> None:
    """Two runs must use distinct thread_ids and complete without cross-talk."""
    first, second = await asyncio.gather(
        _create_run(hitl_client, title="M6 concurrent A", br=GOLDEN_BR_A),
        _create_run(hitl_client, title="M6 concurrent B", br=GOLDEN_BR_B),
    )
    run_a = first["run"]["run_id"]
    run_b = second["run"]["run_id"]
    assert run_a != run_b

    approved_a, approved_b = await asyncio.gather(
        _approve_to_completion(hitl_client, run_a),
        _approve_to_completion(hitl_client, run_b),
    )
    assert approved_a["run"]["status"] == RunStatus.APPROVED
    assert approved_b["run"]["status"] == RunStatus.APPROVED
    assert approved_a["run"]["run_id"] == run_a
    assert approved_b["run"]["run_id"] == run_b
    assert approved_a["run"]["title"] == "M6 concurrent A"
    assert approved_b["run"]["title"] == "M6 concurrent B"
