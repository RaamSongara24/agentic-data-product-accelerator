# ADR 005 — Human-in-the-loop review workflow

| Field | Value |
| --- | --- |
| **ADR** | 005 |
| **Title** | Per-artefact HITL with Approve, Reject, and Request revisions |
| **Status** | Accepted |
| **Date** | 2026-07-20 |

## Context

Governed data product design requires human control. Personas describe workflow participation; **application-level RBAC is not an MVP requirement**. Approvals must be workflow-defined review points with clear semantics, durable across process restarts.

Product semantics: [`PRODUCT_SPEC.md`](../PRODUCT_SPEC.md) §5.4. Durability: ADR 003. Orchestration: ADR 001.

## Decision

- **Each AI-generated artefact is reviewed before progressing** to the next stage.  
- Reviewer decisions:

  | Decision | Effect |
  | --- | --- |
  | **Approve** | Continue to the next stage |
  | **Reject** | **Terminate** the workflow |
  | **Request revisions** | Capture feedback; **regenerate the current artefact**; re-review before continuing |

- HITL is implemented as LangGraph interrupts resumed via API (and lightweight UI).  
- HITL is **not** a configurable in-app permissions engine.  
- Security for data access relies on the **authenticated user’s source-platform permissions**, not application roles.

## Consequences

- Trustworthy, auditable progression through the design lifecycle.  
- Reject is terminal — users start a new run for a fresh attempt.  
- Request revisions requires careful versioning of the current artefact only.  
- UI/API must always expose the three decisions at pending review points.  
- Regeneration mechanics live in architecture/implementation, not the product narrative.

## Alternatives Considered

| Alternative | Why not chosen |
| --- | --- |
| Approve-only gates (no reject/revisions) | Insufficient control for consultants and governance |
| Application RBAC roles for who may approve | Out of MVP scope; workflow points + auth identity suffice |
| Auto-progress without per-artefact review | Conflicts with governed design and Must Have review stories |
| Request revisions restarts the entire pipeline | Wasteful; product requires current-artefact regeneration |
