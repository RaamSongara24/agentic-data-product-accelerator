"""Mapping subgraph helpers: discovery, data mapping, judge routing."""

from __future__ import annotations

import logging
from typing import Any, Literal, cast
from uuid import UUID

from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agentic_data_product.config.settings import get_settings
from agentic_data_product.domain.artefacts import (
    ArtefactRef,
    DataAttribute,
    DataEntity,
    DataModelPayload,
    DataRelationship,
    GovernanceMetadata,
    SourceRef,
    TechnicalRequirementPayload,
)
from agentic_data_product.domain.enums import ArtefactType
from agentic_data_product.domain.lineage import CreateLineageEdgeRequest
from agentic_data_product.domain.user_context import UserContext
from agentic_data_product.integrations.discovery import (
    discover_accessible_objects,
)
from agentic_data_product.integrations.discovery.fixtures import FixtureObject
from agentic_data_product.orchestration.mapping.judge import (
    JudgeOutcome,
    evaluate_mapping_proposal,
)
from agentic_data_product.orchestration.state import HitlGraphState
from agentic_data_product.persistence.store import PostgresArtefactStore

logger = logging.getLogger(__name__)

CONFIGURABLE_SESSION_FACTORY = "session_factory"
StageLiteral = Literal["discovery", "data_mapping", "judge", "persist_mapping", "done"]


def _session_factory(config: RunnableConfig) -> async_sessionmaker[AsyncSession]:
    configurable = config.get("configurable") or {}
    factory = configurable.get(CONFIGURABLE_SESSION_FACTORY)
    if factory is None:
        msg = "Graph config missing session_factory"
        raise RuntimeError(msg)
    return cast(async_sessionmaker[AsyncSession], factory)


def _user_context_from_state(state: HitlGraphState) -> UserContext:
    user_id = state.get("user_id") or state.get("created_by") or "consultant"
    return UserContext(
        user_id=user_id,
        accessible_object_ids=state.get("accessible_object_ids"),
    )


def _fixture_to_dict(obj: FixtureObject) -> dict[str, Any]:
    return obj.model_dump(mode="json")


async def discovery_node(state: HitlGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Fixture-first discovery filtered by user context."""
    _ = config
    ctx = _user_context_from_state(state)
    objects = discover_accessible_objects(ctx)
    logger.info(
        "Discovery for user=%s returned %s objects",
        ctx.user_id,
        len(objects),
    )
    return {
        "discovered_objects": [_fixture_to_dict(o) for o in objects],
        "discovered_object_ids": [o.object_id for o in objects],
        "mapping_stage": "data_mapping",
    }


def _build_mapping_proposal(
    *,
    discovered: list[dict[str, Any]],
    tr: TechnicalRequirementPayload | None,
    feedback: str | None,
    force_empty_sources: bool = False,
) -> dict[str, Any]:
    source_ids = [] if force_empty_sources else [d["object_id"] for d in discovered]
    entities: list[dict[str, Any]] = []
    for obj in discovered:
        attrs = [
            {
                "name": col["name"],
                "data_type": col["data_type"],
                "nullable": col.get("nullable", True),
                "description": col.get("description"),
            }
            for col in obj.get("columns") or []
        ]
        pk = [attrs[0]["name"]] if attrs else []
        entities.append(
            {
                "name": obj["display_name"].replace(" ", ""),
                "description": obj.get("description") or obj["display_name"],
                "attributes": attrs,
                "primary_key": pk,
                "source_object_id": obj["object_id"],
            }
        )

    relationships: list[dict[str, Any]] = []
    names = {e["name"]: e for e in entities}
    if "Orders" in names and "Customers" in names:
        relationships.append(
            {
                "from_entity": "Orders",
                "to_entity": "Customers",
                "from_keys": ["customer_id"],
                "to_keys": ["customer_id"],
                "cardinality": "many_to_one",
            }
        )
    if "Orders" in names and "Products" in names:
        # Prefer product join when both present via shared naming conventions
        order_attrs = {a["name"] for a in names["Orders"]["attributes"]}
        if "product_id" in order_attrs:
            relationships.append(
                {
                    "from_entity": "Orders",
                    "to_entity": "Products",
                    "from_keys": ["product_id"],
                    "to_keys": ["product_id"],
                    "cardinality": "many_to_one",
                }
            )

    notes = []
    if tr is not None:
        notes.append(f"Aligned to TR summary: {tr.summary}")
        notes.append(f"Candidate facts: {', '.join(tr.candidate_facts)}")
    if feedback:
        notes.append(f"Reviewer feedback: {feedback}")

    return {
        "source_object_ids": source_ids,
        "entities": entities,
        "relationships": relationships,
        "notes": notes,
    }


async def data_mapping_node(state: HitlGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Build a canonical mapping proposal from discovered objects + TR."""
    _ = config
    discovered = list(state.get("discovered_objects") or [])
    tr_payload = state.get("tr_payload")
    tr = TechnicalRequirementPayload.model_validate(tr_payload) if tr_payload else None
    force_empty = bool(state.get("force_empty_mapping_sources"))
    proposal = _build_mapping_proposal(
        discovered=discovered,
        tr=tr,
        feedback=state.get("feedback"),
        force_empty_sources=force_empty,
    )
    return {
        "mapping_proposal": proposal,
        "mapping_stage": "judge",
    }


async def mapping_judge_node(state: HitlGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Evaluate mapping proposal; update retry counters / escalation flags."""
    _ = config
    settings = get_settings()
    result = evaluate_mapping_proposal(
        discovered_object_ids=list(state.get("discovered_object_ids") or []),
        mapping_proposal=dict(state.get("mapping_proposal") or {}),
        schema_retry_count=int(state.get("schema_retry_count") or 0),
        logic_retry_count=int(state.get("logic_retry_count") or 0),
        schema_retry_cap=settings.mapping_schema_retry_cap,
        logic_retry_cap=settings.mapping_logic_retry_cap,
        force_outcome=state.get("force_judge_outcome"),
    )
    logger.info(
        "Mapping judge outcome=%s schema_retries=%s logic_retries=%s",
        result.outcome,
        result.schema_retry_count,
        result.logic_retry_count,
    )
    updates: dict[str, Any] = {
        "schema_retry_count": result.schema_retry_count,
        "logic_retry_count": result.logic_retry_count,
        "judge_notes": result.notes,
        "judge_outcome": result.outcome.value,
        "mapping_escalated": result.outcome == JudgeOutcome.ESCALATE,
    }
    if result.outcome == JudgeOutcome.PASS:
        updates["mapping_stage"] = "persist_mapping"
    elif result.outcome == JudgeOutcome.SCHEMA_ISSUE:
        updates["mapping_stage"] = "discovery"
        # Clear force after first application so retries can eventually pass unless
        # the test keeps forcing via state (tests re-set each invoke).
    elif result.outcome == JudgeOutcome.LOGIC_ISSUE:
        updates["mapping_stage"] = "data_mapping"
    else:
        updates["mapping_stage"] = "persist_mapping"
    return updates


def route_after_judge(
    state: HitlGraphState,
) -> Literal["discovery", "data_mapping", "persist_mapping"]:
    stage = state.get("mapping_stage") or "persist_mapping"
    if stage == "discovery":
        return "discovery"
    if stage == "data_mapping":
        return "data_mapping"
    return "persist_mapping"


def _proposal_to_data_model(
    proposal: dict[str, Any],
    *,
    judge_notes: str | None,
    escalated: bool,
) -> DataModelPayload:
    entities: list[DataEntity] = []
    for raw in proposal.get("entities") or []:
        attrs = [
            DataAttribute(
                name=a["name"],
                data_type=a["data_type"],
                nullable=bool(a.get("nullable", True)),
                description=a.get("description"),
            )
            for a in raw.get("attributes") or []
        ]
        entities.append(
            DataEntity(
                name=raw["name"],
                description=raw.get("description"),
                attributes=attrs,
                primary_key=list(raw.get("primary_key") or []),
            )
        )
    if not entities:
        entities.append(
            DataEntity(
                name="PlaceholderEntity",
                description="Escalated mapping with empty proposal",
                attributes=[
                    DataAttribute(name="id", data_type="string", nullable=False),
                ],
                primary_key=["id"],
            )
        )

    relationships = [
        DataRelationship(
            from_entity=r["from_entity"],
            to_entity=r["to_entity"],
            from_keys=list(r["from_keys"]),
            to_keys=list(r["to_keys"]),
            cardinality=r["cardinality"],
        )
        for r in proposal.get("relationships") or []
    ]

    notes = list(proposal.get("notes") or [])
    if judge_notes:
        notes.append(judge_notes)
    if escalated:
        notes.append("ESCALATED: judge retry caps exhausted; human review required.")

    return DataModelPayload(
        name="Mapping data model slice",
        description="Fixture-first source-to-target mapping slice for HITL review",
        entities=entities,
        relationships=relationships,
        mapping_context={
            "source_object_ids": list(proposal.get("source_object_ids") or []),
            "notes": notes,
            "escalated": escalated,
        },
        governance_metadata=GovernanceMetadata(
            access_notes=["Derived only from user-visible fixture objects"],
        ),
    )


async def persist_mapping_node(
    state: HitlGraphState,
    config: RunnableConfig,
) -> dict[str, Any]:
    """Persist Data Model mapping slice and set it as the pending HITL artefact."""
    session_factory = _session_factory(config)
    run_id = UUID(state["run_id"])
    proposal = dict(state.get("mapping_proposal") or {})
    escalated = bool(state.get("mapping_escalated"))
    payload = _proposal_to_data_model(
        proposal,
        judge_notes=state.get("judge_notes"),
        escalated=escalated,
    )

    source_refs = [
        SourceRef(
            system="fixture_catalogue",
            object_id=oid,
            display_name=oid,
        )
        for oid in (proposal.get("source_object_ids") or [])
    ]

    parent_versions: list[ArtefactRef] = []
    tr_id = state.get("tr_artefact_id")
    tr_ver = state.get("tr_artefact_version")
    if tr_id and tr_ver is not None:
        parent_versions.append(
            ArtefactRef(
                artefact_id=UUID(str(tr_id)),
                artefact_type=ArtefactType.TECHNICAL_REQUIREMENT,
                version=int(tr_ver),
                run_id=run_id,
            )
        )

    previous_version = int(state.get("mapping_artefact_version") or 0)
    artefact_id = UUID(state["mapping_artefact_id"]) if state.get("mapping_artefact_id") else None

    async with session_factory() as session:
        store = PostgresArtefactStore(session)
        artefact = await store.save_artefact(
            run_id=run_id,
            artefact_type=ArtefactType.DATA_MODEL,
            payload=payload.model_dump(mode="json"),
            artefact_id=artefact_id,
            created_by=state.get("created_by"),
            source_refs=cast(list[SourceRef | dict[str, Any]], source_refs),
            parent_versions=cast(list[ArtefactRef | dict[str, Any]], parent_versions),
            governance_metadata=payload.governance_metadata,
            validate_payload=True,
        )
        if parent_versions:
            parent = parent_versions[0]
            await store.create_lineage_edge(
                CreateLineageEdgeRequest(
                    run_id=run_id,
                    from_artefact_id=parent.artefact_id,
                    from_version=parent.version,
                    to_artefact_id=artefact.artefact_id,
                    to_version=artefact.version,
                    relationship="derived_from",
                )
            )

    _ = previous_version
    return {
        "mapping_artefact_id": str(artefact.artefact_id),
        "mapping_artefact_version": artefact.version,
        "artefact_id": str(artefact.artefact_id),
        "artefact_version": artefact.version,
        "artefact_type": ArtefactType.DATA_MODEL.value,
        "review_stage": "mapping",
        "decision": None,
        "mapping_stage": "done",
        "force_judge_outcome": None,
        "force_empty_mapping_sources": False,
    }
