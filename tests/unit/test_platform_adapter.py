"""Unit tests for PlatformAdapter / DatabricksAdapter export stub."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentic_data_product.adapters import (
    AdapterApprovalRequiredError,
    AdapterInputError,
    AdapterTargetConfig,
    DatabricksAdapter,
)
from agentic_data_product.domain.artefacts import CanonicalArtefact, ReviewPackagePayload

FIXTURES = Path(__file__).parent / "fixtures" / "approved_artefacts.json"


def _load_approved_artefacts() -> list[CanonicalArtefact]:
    raw = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return [CanonicalArtefact.model_validate(item) for item in raw["artefacts"]]


@pytest.fixture
def approved_artefacts() -> list[CanonicalArtefact]:
    return _load_approved_artefacts()


@pytest.fixture
def adapter() -> DatabricksAdapter:
    return DatabricksAdapter()


@pytest.fixture
def target_config() -> AdapterTargetConfig:
    return AdapterTargetConfig(
        platform="databricks",
        workspace_label="demo-export",
        catalog="main",
        schema_name="sales_dp",
        include_notebooks=True,
    )


def test_databricks_export_from_frozen_approved_fixtures(
    adapter: DatabricksAdapter,
    approved_artefacts: list[CanonicalArtefact],
    target_config: AdapterTargetConfig,
) -> None:
    result = adapter.to_platform(approved_artefacts, target_config)

    assert result.platform == "databricks"
    assert result.mode == "export_stub"
    paths = {asset.path for asset in result.assets}
    assert "manifest.json" in paths
    assert "jobs/pipeline_job.yml" in paths
    assert "unity_catalog/tables.json" in paths
    assert "unity_catalog/metric_view.json" in paths
    assert any(p.startswith("notebooks/") and p.endswith(".py") for p in paths)

    manifest = json.loads(next(a.content for a in result.assets if a.path == "manifest.json"))
    assert manifest["deploy"] is False
    assert manifest["review_package"]["decision_state"] == "approved"
    assert manifest["governance_metadata"] is not None
    assert "commercial" in manifest["governance_metadata"]["sensitivity_labels"]
    assert "internal" in manifest["governance_metadata"]["classifications"]

    tables = json.loads(
        next(a.content for a in result.assets if a.path == "unity_catalog/tables.json")
    )
    assert tables["schema"] == "sales_dp"
    assert any(t["name"].endswith(".FactOrder") for t in tables["tables"])
    assert tables["governance_metadata"]["sensitivity_labels"] == ["commercial"]

    job_yaml = next(a.content for a in result.assets if a.path == "jobs/pipeline_job.yml")
    assert "ingest_sources" in job_yaml
    assert "export_stub" in job_yaml


def test_export_rejects_unapproved_review_package(
    adapter: DatabricksAdapter,
    approved_artefacts: list[CanonicalArtefact],
    target_config: AdapterTargetConfig,
) -> None:
    mutated: list[CanonicalArtefact] = []
    for artefact in approved_artefacts:
        if artefact.artefact_type.value == "review_package":
            payload = ReviewPackagePayload.model_validate(artefact.payload)
            payload = payload.model_copy(update={"decision_state": "pending_review"})
            mutated.append(artefact.model_copy(update={"payload": payload.model_dump(mode="json")}))
        else:
            mutated.append(artefact)

    with pytest.raises(AdapterApprovalRequiredError, match="approved"):
        adapter.to_platform(mutated, target_config)


def test_export_rejects_missing_pipeline_artefact(
    adapter: DatabricksAdapter,
    approved_artefacts: list[CanonicalArtefact],
    target_config: AdapterTargetConfig,
) -> None:
    filtered = [a for a in approved_artefacts if a.artefact_type.value != "pipeline_specification"]
    with pytest.raises(AdapterInputError, match="pipeline"):
        adapter.to_platform(filtered, target_config)


def test_export_derives_only_from_provided_artefacts(
    adapter: DatabricksAdapter,
    approved_artefacts: list[CanonicalArtefact],
    target_config: AdapterTargetConfig,
) -> None:
    """Stub content must reference names from the frozen fixtures, not invented sources."""
    result = adapter.to_platform(approved_artefacts, target_config)
    tables = json.loads(
        next(a.content for a in result.assets if a.path == "unity_catalog/tables.json")
    )
    entity_names = {t["name"].rsplit(".", 1)[-1] for t in tables["tables"]}
    data_model = next(a for a in approved_artefacts if a.artefact_type.value == "data_model")
    expected = {e["name"] for e in data_model.payload["entities"]}
    assert entity_names == expected
    # Must not invent restricted catalogue objects
    bundle_text = "\n".join(a.content for a in result.assets)
    assert "hr.payroll.salaries" not in bundle_text
    assert "security.audit.access_logs" not in bundle_text
