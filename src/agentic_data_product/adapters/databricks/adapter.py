"""Databricks platform adapter — export/stub only (no live deploy)."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Any

from agentic_data_product.adapters.base import PlatformAdapter
from agentic_data_product.adapters.errors import (
    AdapterApprovalRequiredError,
    AdapterInputError,
)
from agentic_data_product.adapters.types import (
    AdapterAsset,
    AdapterResult,
    AdapterTargetConfig,
)
from agentic_data_product.domain.artefacts import (
    CanonicalArtefact,
    GovernanceMetadata,
    ReviewPackagePayload,
    validate_artefact_payload,
)
from agentic_data_product.domain.enums import ArtefactType
from agentic_data_product.observability.errors import ErrorCode
from agentic_data_product.observability.logging_setup import log_event

logger = logging.getLogger(__name__)

_EXPORTABLE_TYPES = frozenset(
    {
        ArtefactType.DATA_MODEL,
        ArtefactType.SEMANTIC_MODEL,
        ArtefactType.PIPELINE_SPECIFICATION,
        ArtefactType.METRIC_DEFINITIONS,
    }
)


def _merge_governance(
    *items: GovernanceMetadata | None,
) -> GovernanceMetadata | None:
    labels: list[str] = []
    classifications: list[str] = []
    notes: list[str] = []
    extra: dict[str, Any] = {}
    found = False
    for item in items:
        if item is None:
            continue
        found = True
        for label in item.sensitivity_labels:
            if label not in labels:
                labels.append(label)
        for classification in item.classifications:
            if classification not in classifications:
                classifications.append(classification)
        for note in item.access_notes:
            if note not in notes:
                notes.append(note)
        extra.update(item.extra)
    if not found:
        return None
    return GovernanceMetadata(
        sensitivity_labels=labels,
        classifications=classifications,
        access_notes=notes,
        extra=extra,
    )


def _gov_dump(*items: GovernanceMetadata | None) -> dict[str, Any] | None:
    merged = _merge_governance(*items)
    return merged.model_dump(mode="json") if merged else None


def _index_by_type(
    artefacts: Sequence[CanonicalArtefact],
) -> dict[ArtefactType, CanonicalArtefact]:
    indexed: dict[ArtefactType, CanonicalArtefact] = {}
    for artefact in artefacts:
        # Prefer highest version when duplicates appear in fixtures.
        existing = indexed.get(artefact.artefact_type)
        if existing is None or artefact.version >= existing.version:
            indexed[artefact.artefact_type] = artefact
    return indexed


def _require_approved_review_package(
    indexed: dict[ArtefactType, CanonicalArtefact],
) -> CanonicalArtefact:
    rp = indexed.get(ArtefactType.REVIEW_PACKAGE)
    if rp is None:
        raise AdapterApprovalRequiredError(
            "Export requires an approved Review Package artefact",
            context={"missing": ArtefactType.REVIEW_PACKAGE.value},
        )
    payload = validate_artefact_payload(ArtefactType.REVIEW_PACKAGE, rp.payload)
    assert isinstance(payload, ReviewPackagePayload)
    if payload.decision_state != "approved":
        raise AdapterApprovalRequiredError(
            "Review Package must be approved before platform export",
            code=ErrorCode.ADAPTER_APPROVAL_REQUIRED,
            context={"decision_state": payload.decision_state},
        )
    return rp


def _yaml_escape(value: str) -> str:
    if any(ch in value for ch in (":", "#", "{", "}", "[", "]", ",", "&", "*", "!", "|")):
        return json.dumps(value)
    return value


def _to_simple_yaml(data: dict[str, Any], *, indent: int = 0) -> str:
    """Minimal YAML emitter for stub job definitions (no PyYAML dependency)."""
    lines: list[str] = []
    prefix = "  " * indent
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_to_simple_yaml(value, indent=indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"{prefix}-")
                    # Indent dict items under list marker
                    nested = _to_simple_yaml(item, indent=indent + 1)
                    for nested_line in nested.splitlines():
                        lines.append(f"  {nested_line}" if nested_line else nested_line)
                else:
                    lines.append(f"{prefix}- {_yaml_escape(str(item))}")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif value is None:
            lines.append(f"{prefix}{key}: null")
        else:
            lines.append(f"{prefix}{key}: {_yaml_escape(str(value))}")
    return "\n".join(lines) + ("\n" if lines else "")


class DatabricksAdapter(PlatformAdapter):
    """Export approved canonical artefacts as Databricks-shaped stub files.

    Does **not** deploy jobs, notebooks, or Unity Catalog objects into a workspace.
    """

    @property
    def platform_id(self) -> str:
        return "databricks"

    def to_platform(
        self,
        artefacts: Sequence[CanonicalArtefact],
        target_config: AdapterTargetConfig,
    ) -> AdapterResult:
        if target_config.platform not in ("databricks", self.platform_id):
            raise AdapterInputError(
                f"DatabricksAdapter cannot target platform={target_config.platform!r}",
                context={"platform": target_config.platform},
            )

        indexed = _index_by_type(artefacts)
        review_package = _require_approved_review_package(indexed)

        missing = sorted(t.value for t in _EXPORTABLE_TYPES if t not in indexed)
        if missing:
            raise AdapterInputError(
                "Approved export requires pipeline, data model, semantic model, "
                "and metric definition artefacts",
                context={"missing_artefact_types": missing},
            )

        data_model = indexed[ArtefactType.DATA_MODEL]
        semantic = indexed[ArtefactType.SEMANTIC_MODEL]
        pipeline = indexed[ArtefactType.PIPELINE_SPECIFICATION]
        metrics = indexed[ArtefactType.METRIC_DEFINITIONS]

        bundle_gov = _merge_governance(
            review_package.governance_metadata,
            data_model.governance_metadata,
            semantic.governance_metadata,
            pipeline.governance_metadata,
            metrics.governance_metadata,
        )

        catalog = target_config.catalog
        schema = target_config.schema_name
        fqn_prefix = f"{catalog}.{schema}"

        manifest: dict[str, Any] = {
            "platform": self.platform_id,
            "mode": "export_stub",
            "workspace_label": target_config.workspace_label,
            "catalog": catalog,
            "schema": schema,
            "source_run_id": str(review_package.run_id),
            "review_package": {
                "artefact_id": str(review_package.artefact_id),
                "version": review_package.version,
                "decision_state": "approved",
            },
            "artefacts": {
                t.value: {
                    "artefact_id": str(indexed[t].artefact_id),
                    "version": indexed[t].version,
                }
                for t in (
                    ArtefactType.DATA_MODEL,
                    ArtefactType.SEMANTIC_MODEL,
                    ArtefactType.PIPELINE_SPECIFICATION,
                    ArtefactType.METRIC_DEFINITIONS,
                    ArtefactType.REVIEW_PACKAGE,
                )
            },
            "governance_metadata": _gov_dump(bundle_gov),
            "deploy": False,
            "note": "Stub export only — no live Databricks deployment",
        }

        pipeline_payload = pipeline.payload
        stages = pipeline_payload.get("stages") or []
        job_stub: dict[str, Any] = {
            "resource_name": f"{fqn_prefix}.pipeline_job",
            "job_clusters": [],
            "tasks": [
                {
                    "task_key": str(stage.get("name", f"stage_{idx}")),
                    "description": str(stage.get("description", "")),
                    "depends_on": list(stage.get("dependencies") or []),
                    "notebook_path": (
                        f"/Shared/exports/{schema}/notebooks/{stage.get('name', f'stage_{idx}')}"
                    ),
                }
                for idx, stage in enumerate(stages)
                if isinstance(stage, dict)
            ],
            "tags": {
                "source": "agentic_data_product",
                "mode": "export_stub",
            },
            "governance_metadata": _gov_dump(pipeline.governance_metadata, bundle_gov),
        }

        tables_stub: dict[str, Any] = {
            "catalog": catalog,
            "schema": schema,
            "tables": [],
            "governance_metadata": _gov_dump(data_model.governance_metadata, bundle_gov),
        }
        for entity in data_model.payload.get("entities") or []:
            if not isinstance(entity, dict):
                continue
            name = str(entity.get("name", "entity"))
            tables_stub["tables"].append(
                {
                    "name": f"{fqn_prefix}.{name}",
                    "comment": entity.get("description"),
                    "columns": [
                        {
                            "name": attr.get("name"),
                            "type": attr.get("data_type"),
                            "nullable": attr.get("nullable", True),
                            "governance_metadata": attr.get("governance_metadata"),
                        }
                        for attr in (entity.get("attributes") or [])
                        if isinstance(attr, dict)
                    ],
                    "primary_key": list(entity.get("primary_key") or []),
                }
            )

        metrics_view: dict[str, Any] = {
            "name": f"{fqn_prefix}.metric_view",
            "semantic_model": semantic.payload.get("name"),
            "metrics": metrics.payload.get("metrics") or [],
            "dimensions": semantic.payload.get("dimensions") or [],
            "governance_metadata": _gov_dump(
                semantic.governance_metadata,
                metrics.governance_metadata,
                bundle_gov,
            ),
        }

        assets: list[AdapterAsset] = [
            AdapterAsset(
                path="manifest.json",
                kind="json",
                content=json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                content_type="application/json",
                governance_metadata=bundle_gov,
                source_artefact_types=[ArtefactType.REVIEW_PACKAGE.value],
            ),
            AdapterAsset(
                path="jobs/pipeline_job.yml",
                kind="yaml",
                content=_to_simple_yaml(job_stub),
                content_type="application/x-yaml",
                governance_metadata=_merge_governance(pipeline.governance_metadata, bundle_gov),
                source_artefact_types=[ArtefactType.PIPELINE_SPECIFICATION.value],
            ),
            AdapterAsset(
                path="unity_catalog/tables.json",
                kind="json",
                content=json.dumps(tables_stub, indent=2, sort_keys=True) + "\n",
                content_type="application/json",
                governance_metadata=_merge_governance(data_model.governance_metadata, bundle_gov),
                source_artefact_types=[ArtefactType.DATA_MODEL.value],
            ),
            AdapterAsset(
                path="unity_catalog/metric_view.json",
                kind="json",
                content=json.dumps(metrics_view, indent=2, sort_keys=True) + "\n",
                content_type="application/json",
                governance_metadata=_merge_governance(
                    semantic.governance_metadata,
                    metrics.governance_metadata,
                    bundle_gov,
                ),
                source_artefact_types=[
                    ArtefactType.SEMANTIC_MODEL.value,
                    ArtefactType.METRIC_DEFINITIONS.value,
                ],
            ),
        ]

        if target_config.include_notebooks:
            for idx, stage in enumerate(stages):
                if not isinstance(stage, dict):
                    continue
                stage_name = str(stage.get("name", f"stage_{idx}"))
                notebook = (
                    f"# Databricks notebook source (export stub)\n"
                    f"# MAGIC %md\n"
                    f"# MAGIC ## Stage: {stage_name}\n"
                    f"# MAGIC {stage.get('description', '')}\n"
                    f"# MAGIC\n"
                    f"# MAGIC Derived from approved Pipeline Specification only.\n"
                    f"# MAGIC Live deploy is not performed by this adapter.\n"
                    f"\n"
                    f"print({json.dumps(f'Stub stage: {stage_name}')})\n"
                )
                assets.append(
                    AdapterAsset(
                        path=f"notebooks/{stage_name}.py",
                        kind="notebook",
                        content=notebook,
                        content_type="text/x-python",
                        governance_metadata=_merge_governance(
                            pipeline.governance_metadata, bundle_gov
                        ),
                        source_artefact_types=[ArtefactType.PIPELINE_SPECIFICATION.value],
                        metadata={"stage_kind": stage.get("kind")},
                    )
                )

        result = AdapterResult(
            platform=self.platform_id,
            mode="export_stub",
            assets=assets,
            warnings=[
                "Export stub only — no jobs, notebooks, or UC objects were deployed",
            ],
            metadata={
                "asset_count": len(assets),
                "catalog": catalog,
                "schema": schema,
            },
        )
        log_event(
            logger,
            "adapter_export_completed",
            platform=self.platform_id,
            asset_count=len(assets),
            run_id=str(review_package.run_id),
        )
        return result
