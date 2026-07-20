# Architecture Decision Records

This directory records **why** major architectural choices were made.

| ADR | Title | Status |
| --- | --- | --- |
| [000](000-template.md) | Template | — |
| [001](001-langgraph-orchestration.md) | LangGraph for agent orchestration | Accepted |
| [002](002-canonical-artefacts.md) | Canonical artefacts as source of truth | Accepted |
| [003](003-postgresql-persistence.md) | PostgreSQL persistence and checkpointer | Accepted |
| [004](004-platform-adapter-architecture.md) | Platform adapter architecture | Accepted |
| [005](005-human-in-the-loop-workflow.md) | Human-in-the-loop review workflow | Accepted |

New decisions: copy `000-template.md`, use the next number, and link from this index and from PRs that implement the decision.

Authoritative product/architecture detail remains in [`../PRODUCT_SPEC.md`](../PRODUCT_SPEC.md) and [`../ARCHITECTURE.md`](../ARCHITECTURE.md).
