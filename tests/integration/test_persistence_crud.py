"""Integration tests for M1 persistence development endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_and_artefact_crud(integration_client: AsyncClient) -> None:
    create_run = await integration_client.post(
        "/dev/runs",
        json={"name": "m1-dev-run", "metadata": {"source": "integration-test"}},
    )
    assert create_run.status_code == 201
    run_payload = create_run.json()
    run_id = run_payload["run_id"]

    create_artefact = await integration_client.post(
        "/dev/artefacts",
        json={
            "run_id": run_id,
            "artefact_type": "business_requirement",
            "payload": {
                "intent": "Validate persistence",
                "objectives": ["Create and retrieve artefacts"],
                "constraints": ["No business logic in M1"],
                "success_criteria": ["CRUD works"],
            },
            "metadata": {"test_case": "run_and_artefact_crud"},
        },
    )
    assert create_artefact.status_code == 201
    artefact_payload = create_artefact.json()
    artefact_id = artefact_payload["artefact_id"]

    get_artefact = await integration_client.get(f"/dev/artefacts/{artefact_id}")
    assert get_artefact.status_code == 200
    assert get_artefact.json()["payload"]["intent"] == "Validate persistence"

    list_artefacts = await integration_client.get("/dev/artefacts", params={"run_id": run_id})
    assert list_artefacts.status_code == 200
    items: list[dict[str, Any]] = list_artefacts.json()
    assert len(items) == 1
    assert items[0]["artefact_id"] == artefact_id

    audit = await integration_client.get("/dev/audit", params={"run_id": run_id})
    assert audit.status_code == 200
    events = audit.json()
    assert len(events) >= 2
    event_types = [item["event_type"] for item in events]
    assert "run_created" in event_types
    assert "artefact_created" in event_types


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lineage_edge(integration_client: AsyncClient) -> None:
    run = await integration_client.post("/dev/runs", json={"name": "lineage-run"})
    assert run.status_code == 201
    run_id = run.json()["run_id"]

    a1 = await integration_client.post(
        "/dev/artefacts",
        json={
            "run_id": run_id,
            "artefact_type": "technical_requirement",
            "payload": {
                "expected_behavior": ["x"],
                "entities": ["orders"],
                "transformations": [],
                "governance_requirements": [],
                "acceptance_criteria": [],
            },
        },
    )
    a2 = await integration_client.post(
        "/dev/artefacts",
        json={
            "run_id": run_id,
            "artefact_type": "data_model",
            "payload": {
                "datasets": ["orders"],
                "entities": ["fact_orders"],
                "attributes": ["order_id"],
                "keys": ["order_id"],
                "relationships": [],
                "governance_metadata": {},
            },
        },
    )
    assert a1.status_code == 201
    assert a2.status_code == 201

    edge = await integration_client.post(
        "/dev/lineage",
        json={
            "run_id": run_id,
            "from_artefact_id": a1.json()["artefact_id"],
            "to_artefact_id": a2.json()["artefact_id"],
            "relation": "derived_from",
        },
    )
    assert edge.status_code == 201
    edge_id = edge.json()["edge_id"]

    list_edges = await integration_client.get("/dev/lineage", params={"run_id": run_id})
    assert list_edges.status_code == 200
    edges = list_edges.json()
    assert len(edges) == 1
    assert edges[0]["edge_id"] == edge_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_artefact_payload_validation(integration_client: AsyncClient) -> None:
    run = await integration_client.post("/dev/runs", json={"name": "validation-run"})
    assert run.status_code == 201
    run_id = run.json()["run_id"]

    invalid = await integration_client.post(
        "/dev/artefacts",
        json={
            "run_id": run_id,
            "artefact_type": "business_requirement",
            "payload": {
                # Missing required "intent"
                "objectives": ["x"],
                "constraints": [],
                "success_criteria": [],
            },
        },
    )
    assert invalid.status_code == 422
