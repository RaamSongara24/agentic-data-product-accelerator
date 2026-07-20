# ADR 004 — Platform adapter architecture

| Field | Value |
| --- | --- |
| **ADR** | 004 |
| **Title** | Platform adapters for vendor-specific materialisation |
| **Status** | Accepted |
| **Date** | 2026-07-20 |

## Context

Databricks is available for development and demonstration and is the **first implementation target**. The product must remain technology agnostic so future targets (Microsoft Fabric, Snowflake, Power BI, and others) do not force rewrites of upstream agents.

See [`ARCHITECTURE.md`](../ARCHITECTURE.md) §11 and ADR 002.

## Decision

Introduce a **PlatformAdapter** boundary:

- Inputs: **approved** canonical artefacts.  
- Outputs: platform-specific assets or export bundles.  
- **DatabricksAdapter** is the first implementation (stub/export acceptable for early milestones; live deploy is not an MVP acceptance blocker).  
- Agents **do not** call adapter write APIs during generation.  
- Discovery may read source platforms **as the authenticated user** via integrations — that is not adapter materialisation.

## Consequences

- Clear separation of design-time (canonical) vs deploy-time (platform).  
- Additional platforms are new adapter modules + tests.  
- MVP can demo value without production deploy.  
- Adapter authors must not leak vendor types into domain models.

## Alternatives Considered

| Alternative | Why not chosen |
| --- | --- |
| Hard-code Databricks generation inside agents | Vendor lock-in; contradicts product positioning |
| Single “exporter” with switch statements everywhere | Poor modularity; harder to test and own per platform |
| Defer all adapter thinking until after MVP | Would entangle vendor concerns into early agent prompts and schemas |
