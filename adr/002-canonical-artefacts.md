# ADR 002 — Canonical artefacts as the data product source of truth

| Field | Value |
| --- | --- |
| **ADR** | 002 |
| **Title** | Technology-agnostic canonical artefacts |
| **Status** | Accepted |
| **Date** | 2026-07-20 |

## Context

The product is an **Agentic Data Product Design Platform**, not a Databricks (or other vendor) code generator. Downstream platforms will differ (Databricks first; later Fabric, Snowflake, Power BI, etc.). Agents, reviewers, audit, and lineage need a stable, portable contract.

Catalogue and definitions: [`PRODUCT_SPEC.md`](../PRODUCT_SPEC.md) §5.

## Decision

Agents produce and revise only these **seven versioned canonical artefacts**:

1. Business Requirement  
2. Technical Requirement  
3. Semantic Model  
4. Data Model  
5. Pipeline Specification  
6. Metric Definitions  
7. Review Package  

They are **technology agnostic**. Platform-specific outputs are created by **adapters** from approved artefacts (ADR 004). Artefacts are typed (Pydantic), versioned, and linked in lineage.

## Consequences

- Clear review surfaces and auditability.  
- New platforms extend adapters without rewriting agent graphs.  
- Requires discipline: no “just emit a notebook” shortcuts in agent nodes.  
- Schema evolution must be versioned carefully.

## Alternatives Considered

| Alternative | Why not chosen |
| --- | --- |
| Generate Databricks assets directly from agents | Couples the product to one vendor; blocks multi-platform strategy |
| Store only chat transcripts / free-form Markdown | Weak contracts, poor lineage, hard to adapt or test |
| Separate “IR” plus vendor docs as co-equal sources of truth | Ambiguous authority; reviewers need one canonical set |
