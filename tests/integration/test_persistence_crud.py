"""Integration tests for artefact versioning, audit, and lineage persistence."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient


def _business_payload(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "Regional sales",
        "intent": "Track revenue",
        "objectives": ["Daily regional totals"],
        "constraints": [],
        "success_criteria": ["Matches finance"],
    }
    base.update(overrides)
    return base


@pytest.mark.integration
@pytest.mark.asyncio
async def test_persistence_crud_flow(integration_client: AsyncClient) -> None:
    # Create run
    run_resp = await integration_client.post(
        "/dev/runs",
        json={"title": "M1 integration run", "created_by": "tester"},
    )
    assert run_resp.status_code == 201, run_resp.text
    run = run_resp.json()
    run_id = run["run_id"]
    assert run["status"] == "created"

    # Save artefact v1
    art_resp = await integration_client.post(
        "/dev/artefacts",
        json={
            "run_id": run_id,
            "artefact_type": "business_requirement",
            "payload": _business_payload(),
            "created_by": "tester",
        },
    )
    assert art_resp.status_code == 201, art_resp.text
    art_v1 = art_resp.json()
    assert art_v1["version"] == 1
    artefact_id = art_v1["artefact_id"]

    # Save artefact v2 (same type, auto version)
    art_v2_resp = await integration_client.post(
        "/dev/artefacts",
        json={
            "run_id": run_id,
            "artefact_type": "business_requirement",
            "payload": _business_payload(title="Regional sales revised"),
            "created_by": "tester",
        },
    )
    assert art_v2_resp.status_code == 201, art_v2_resp.text
    art_v2 = art_v2_resp.json()
    assert art_v2["version"] == 2
    assert art_v2["artefact_id"] == artefact_id

    # Unique (run, type, version) conflict
    conflict = await integration_client.post(
        "/dev/artefacts",
        json={
            "run_id": run_id,
            "artefact_type": "business_requirement",
            "payload": _business_payload(),
            "version": 1,
        },
    )
    assert conflict.status_code == 409

    # Get specific / latest
    get_v1 = await integration_client.get(f"/dev/artefacts/{artefact_id}", params={"version": 1})
    assert get_v1.status_code == 200
    assert get_v1.json()["payload"]["title"] == "Regional sales"

    get_latest = await integration_client.get(f"/dev/artefacts/{artefact_id}")
    assert get_latest.status_code == 200
    assert get_latest.json()["version"] == 2

    # Technical requirement for lineage target
    tech_resp = await integration_client.post(
        "/dev/artefacts",
        json={
            "run_id": run_id,
            "artefact_type": "technical_requirement",
            "payload": {
                "summary": "Tech view",
                "behaviours": ["Aggregate orders"],
            },
        },
    )
    assert tech_resp.status_code == 201, tech_resp.text
    tech = tech_resp.json()

    # Lineage
    lineage_resp = await integration_client.post(
        "/dev/lineage",
        json={
            "run_id": run_id,
            "from_artefact_id": artefact_id,
            "from_version": 2,
            "to_artefact_id": tech["artefact_id"],
            "to_version": 1,
            "relationship": "derived_from",
        },
    )
    assert lineage_resp.status_code == 201, lineage_resp.text

    listed_lineage = await integration_client.get("/dev/lineage", params={"run_id": run_id})
    assert listed_lineage.status_code == 200
    edges = listed_lineage.json()
    assert len(edges) == 1
    assert edges[0]["from_version"] == 2

    # Audit includes run + artefacts + lineage
    audit_resp = await integration_client.get("/dev/audit", params={"run_id": run_id})
    assert audit_resp.status_code == 200
    actions = [event["action"] for event in audit_resp.json()]
    assert "run_created" in actions
    assert actions.count("artefact_created") >= 3
    assert "lineage_created" in actions

    # List artefacts for run
    listed = await integration_client.get(f"/dev/runs/{run_id}/artefacts")
    assert listed.status_code == 200
    assert len(listed.json()) == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalid_artefact_payload_returns_422(integration_client: AsyncClient) -> None:
    run_resp = await integration_client.post("/dev/runs", json={"title": "validation run"})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["run_id"]

    bad = await integration_client.post(
        "/dev/artefacts",
        json={
            "run_id": run_id,
            "artefact_type": "business_requirement",
            "payload": {"title": "missing required fields"},
        },
    )
    assert bad.status_code == 422, bad.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_artefact_for_missing_run_returns_404(integration_client: AsyncClient) -> None:
    missing_run = uuid4()
    resp = await integration_client.post(
        "/dev/artefacts",
        json={
            "run_id": str(missing_run),
            "artefact_type": "business_requirement",
            "payload": _business_payload(),
        },
    )
    assert resp.status_code == 404
