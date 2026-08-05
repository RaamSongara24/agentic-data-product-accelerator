"""Shared types for platform adapters (ADR 004)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from agentic_data_product.domain.artefacts import GovernanceMetadata


class AdapterTargetConfig(BaseModel):
    """Target-platform configuration hints (never canonical artefact fields)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    platform: str = Field(min_length=1, description="Logical platform id, e.g. databricks")
    workspace_label: str | None = Field(
        default=None,
        description="Human label for the export bundle (not a live workspace id)",
    )
    catalog: str = Field(default="main", min_length=1)
    schema_name: str = Field(default="data_products", min_length=1, alias="schema")
    export_format: Literal["bundle"] = "bundle"
    include_notebooks: bool = True


class AdapterAsset(BaseModel):
    """One exported platform-shaped file or stub asset (no live deploy)."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, description="Relative path inside the export bundle")
    kind: Literal["yaml", "json", "notebook", "markdown", "other"] = "json"
    content: str = Field(description="File contents as text")
    content_type: str = Field(default="application/json")
    governance_metadata: GovernanceMetadata | None = None
    source_artefact_types: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AdapterResult(BaseModel):
    """Result of mapping approved canonical artefacts to platform artefacts."""

    model_config = ConfigDict(extra="forbid")

    platform: str = Field(min_length=1)
    mode: Literal["export_stub"] = "export_stub"
    assets: list[AdapterAsset] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
