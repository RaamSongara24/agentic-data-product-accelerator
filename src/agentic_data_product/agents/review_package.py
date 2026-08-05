"""Assemble the Review Package from pinned artefact versions and evidence."""

from __future__ import annotations

from agentic_data_product.domain.artefacts import ArtefactRef, ReviewPackagePayload


def assemble_review_package(
    *,
    title: str,
    pinned: list[ArtefactRef],
    assumptions: list[str] | None = None,
    traceability_notes: list[str] | None = None,
    validation_results: list[str] | None = None,
    unresolved_questions: list[str] | None = None,
    recommendations: list[str] | None = None,
    feedback: str | None = None,
) -> ReviewPackagePayload:
    """Build a Review Package payload for HITL (no LLM required)."""
    assumptions_list = list(assumptions or [])
    if not assumptions_list:
        assumptions_list = [
            "Kimball star-schema conventions guide Semantic and Data Models",
            "Discovery and mapping used only user-visible source objects",
            "Pipeline Specification is declarative and not vendor-executable in MVP",
        ]
    if feedback:
        assumptions_list.append(f"Reviewer feedback on prior package draft: {feedback}")

    trace = list(traceability_notes or [])
    if not trace:
        trace = [
            "Business Requirement → Technical Requirement → mapping Data Model",
            "Technical Requirement + mapping → Semantic Model + Data Model",
            "Modelling artefacts → Pipeline Specification + Metric Definitions",
            "All prior artefacts pinned into this Review Package",
        ]
    for ref in pinned:
        trace.append(f"Pinned {ref.artefact_type.value} id={ref.artefact_id} v{ref.version}")

    validations = list(validation_results or [])
    questions = list(unresolved_questions or [])
    if not questions:
        questions = [
            "Confirm grain of order_amount with business stakeholders before publish",
        ]

    recs = list(recommendations or [])
    if not recs:
        recs = [
            "Approve the Review Package to mark the design path complete in-platform",
            "Canonical artefacts are the product; optional Databricks export is an "
            "adapter stub after approval (no live deploy)",
        ]

    summary = f"Consolidated review of {len(pinned)} pinned artefact version(s) for '{title}'"
    if feedback:
        summary = f"{summary} (revised)"

    return ReviewPackagePayload(
        title=f"Review Package: {title}",
        summary=summary,
        pinned_artefacts=pinned,
        assumptions=assumptions_list,
        traceability_notes=trace,
        validation_results=validations,
        unresolved_questions=questions,
        recommendations=recs,
        decision_state="pending_review",
    )
