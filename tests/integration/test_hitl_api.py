"""Integration tests for M4 HITL APIs (full seven-artefact path) and durable resume."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from agentic_data_product.app.main import create_app
from agentic_data_product.config.settings import get_settings
from agentic_data_product.domain.enums import ArtefactType, ReviewDecisionKind, RunStatus
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
        "All seven canonical artefacts approved via Review Package",
    ],
    "stakeholders": ["data_consultant"],
}

# HITL sequence after create_run (waiting on TR)
STAGE_ORDER = (
    "technical_requirement",
    "data_model",  # mapping slice
    "semantic_model",  # modelling
    "metric_definitions",  # implementation
    "review_package",
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


async def _create_run(client: AsyncClient, *, title: str = "M4 run") -> dict:
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


async def _approve(client: AsyncClient, run_id: str, *, comments: str = "ok") -> dict:
    resp = await client.post(
        f"/runs/{run_id}/reviews",
        json={
            "decision": ReviewDecisionKind.APPROVE,
            "comments": comments,
            "reviewer_id": "consultant",
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _approve_until(
    client: AsyncClient,
    run_id: str,
    *,
    until_type: str,
) -> dict:
    """Approve successive HITL gates until pending artefact type matches ``until_type``."""
    body = (await client.get(f"/runs/{run_id}")).json()
    for _ in range(10):
        if body["run"]["status"] != RunStatus.WAITING_FOR_REVIEW:
            break
        pending_type = body["pending_review"]["artefact"]["artefact_type"]
        if pending_type == until_type:
            return body
        body = await _approve(client, run_id, comments=f"approve {pending_type}")
    raise AssertionError(f"Did not reach pending type {until_type!r}; last={body}")


@pytest.mark.integration
async def test_create_run_reaches_tr_waiting_for_review(hitl_client: AsyncClient) -> None:
    body = await _create_run(hitl_client, title="M4 TR gate")
    assert body["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
    assert body["pending_review"] is not None
    assert body["pending_review"]["artefact"]["artefact_type"] == "technical_requirement"
    assert body["pending_review"]["artefact"]["version"] == 1
    assert body["latest_artefact"]["artefact_type"] == "technical_requirement"


@pytest.mark.integration
async def test_approve_all_produces_seven_artefacts(
    hitl_client: AsyncClient,
    hitl_app: FastAPI,
) -> None:
    """M4 exit criterion: approve-all path produces all seven artefacts via API."""
    from agentic_data_product.orchestration.runner import HitlRunner
    from agentic_data_product.persistence.store import PostgresArtefactStore

    created = await _create_run(hitl_client, title="approve all seven")
    run_id = created["run"]["run_id"]
    runner: HitlRunner = hitl_app.state.hitl_runner

    seen_stages: list[str] = []
    body = created
    for _ in range(12):
        if body["run"]["status"] != RunStatus.WAITING_FOR_REVIEW:
            break
        pending_type = body["pending_review"]["artefact"]["artefact_type"]
        seen_stages.append(pending_type)

        if pending_type == "data_model":
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

        body = await _approve(
            hitl_client,
            run_id,
            comments=f"approve {pending_type}",
        )

    assert body["run"]["status"] == RunStatus.APPROVED
    assert body["pending_review"] is None
    assert seen_stages == list(STAGE_ORDER)

    async with runner._session_factory() as session:
        store = PostgresArtefactStore(session)
        refs = await store.list_artefacts_for_run(UUID(run_id))
        types = {r.artefact_type for r in refs}
        assert types == {
            ArtefactType.BUSINESS_REQUIREMENT,
            ArtefactType.TECHNICAL_REQUIREMENT,
            ArtefactType.SEMANTIC_MODEL,
            ArtefactType.DATA_MODEL,
            ArtefactType.PIPELINE_SPECIFICATION,
            ArtefactType.METRIC_DEFINITIONS,
            ArtefactType.REVIEW_PACKAGE,
        }
        rp_refs = [r for r in refs if r.artefact_type == ArtefactType.REVIEW_PACKAGE]
        latest_rp = max(rp_refs, key=lambda r: r.version)
        rp = await store.get_artefact(latest_rp.artefact_id, latest_rp.version)
        assert rp.payload.get("validation_results")
        assert any("PASS:" in str(v) or "FAIL:" in str(v) for v in rp.payload["validation_results"])
        assert rp.payload.get("decision_state") == "approved"


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
async def test_reject_mid_stage_modelling_terminates(hitl_client: AsyncClient) -> None:
    """Reject at a mid-stage (modelling) terminates the run."""
    created = await _create_run(hitl_client, title="reject modelling")
    run_id = created["run"]["run_id"]
    await _approve_until(hitl_client, run_id, until_type="semantic_model")
    rejected = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={"decision": ReviewDecisionKind.REJECT, "comments": "Bad model"},
    )
    assert rejected.json()["run"]["status"] == RunStatus.TERMINATED


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
async def test_request_revisions_on_metrics_only_regenerates_metrics(
    hitl_client: AsyncClient,
    hitl_app: FastAPI,
) -> None:
    """Request revisions on Metric Definitions regenerates only that stage."""
    created = await _create_run(hitl_client, title="revise metrics only")
    run_id = created["run"]["run_id"]
    body = await _approve_until(hitl_client, run_id, until_type="metric_definitions")
    metrics_id = body["pending_review"]["artefact"]["artefact_id"]
    metrics_v1 = body["pending_review"]["artefact"]["version"]
    assert metrics_v1 == 1

    from agentic_data_product.orchestration.runner import HitlRunner
    from agentic_data_product.persistence.store import PostgresArtefactStore

    runner: HitlRunner = hitl_app.state.hitl_runner
    async with runner._session_factory() as session:
        store = PostgresArtefactStore(session)
        before = await store.list_artefacts_for_run(UUID(run_id))
    pipe_before = {
        (r.artefact_id, r.version)
        for r in before
        if r.artefact_type == ArtefactType.PIPELINE_SPECIFICATION
    }
    sm_before = {
        (r.artefact_id, r.version) for r in before if r.artefact_type == ArtefactType.SEMANTIC_MODEL
    }

    revised = await hitl_client.post(
        f"/runs/{run_id}/reviews",
        json={
            "decision": ReviewDecisionKind.REQUEST_REVISIONS,
            "comments": "Tighten metric filters for order_amount",
            "reviewer_id": "consultant",
        },
    )
    assert revised.status_code == 200, revised.text
    rev = revised.json()
    assert rev["run"]["status"] == RunStatus.WAITING_FOR_REVIEW
    assert rev["pending_review"]["artefact"]["artefact_type"] == "metric_definitions"
    assert rev["pending_review"]["artefact"]["artefact_id"] == metrics_id
    assert rev["pending_review"]["artefact"]["version"] == metrics_v1 + 1

    async with runner._session_factory() as session:
        store = PostgresArtefactStore(session)
        after = await store.list_artefacts_for_run(UUID(run_id))
    pipe_after = {
        (r.artefact_id, r.version)
        for r in after
        if r.artefact_type == ArtefactType.PIPELINE_SPECIFICATION
    }
    sm_after = {
        (r.artefact_id, r.version) for r in after if r.artefact_type == ArtefactType.SEMANTIC_MODEL
    }
    assert pipe_after == pipe_before
    assert sm_after == sm_before
    assert not any(r.artefact_type == ArtefactType.REVIEW_PACKAGE for r in after)


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
    # Approve through Review Package to terminal approved
    body = created
    for _ in range(12):
        if body["run"]["status"] != RunStatus.WAITING_FOR_REVIEW:
            break
        body = await _approve(hitl_client, run_id)
    assert body["run"]["status"] == RunStatus.APPROVED
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

            body = revised.json()
            for _ in range(12):
                if body["run"]["status"] != RunStatus.WAITING_FOR_REVIEW:
                    break
                body = (
                    await client2.post(
                        f"/runs/{run_id}/reviews",
                        json={"decision": ReviewDecisionKind.APPROVE},
                    )
                ).json()
            assert body["run"]["status"] == RunStatus.APPROVED

    get_settings.cache_clear()
    set_database(None)
