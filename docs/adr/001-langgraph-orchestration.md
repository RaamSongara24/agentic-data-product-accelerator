# ADR 001 — LangGraph for agent orchestration

| Field | Value |
| --- | --- |
| **ADR** | 001 |
| **Title** | LangGraph for multi-agent orchestration |
| **Status** | Accepted |
| **Date** | 2026-07-20 |

## Context

The platform must coordinate multiple specialised agents (requirements, discovery, mapping, modelling, implementation, metrics), support retries, and pause for human review. The implementation stack is Python-based (FastAPI). Orchestration must be durable, testable, and the source of truth for control flow — not ad-hoc scripts or undocumented prompt chains.

See [`ARCHITECTURE.md`](../ARCHITECTURE.md) and [`PRODUCT_SPEC.md`](../PRODUCT_SPEC.md).

## Decision

Use **LangGraph** as the orchestration framework for the agent workflow.

- One **fixed compiled graph** for MVP (runtime config profiles for models/prompts — not a visual workflow builder).  
- **Subgraphs** for Mapping and Implementation paths.  
- Graph state holds control data and **artefact references**; large payloads live in the artefact store.  
- Internal agent loops (e.g. mapping judge) are **capped** with escalation to HITL.

## Consequences

- HITL maps naturally to interrupts/resume with a checkpointer (see ADR 003, ADR 005).  
- Control-flow tests can target the graph independently of the UI.  
- Team must invest in LangGraph patterns (state schema, subgraphs, interrupts).  
- Avoid embedding side effects that cannot be reconciled with checkpoint boundaries.

## Alternatives Considered

| Alternative | Why not chosen |
| --- | --- |
| Plain LangChain chains / custom asyncio FSM | Weaker durable HITL and subgraph composition; more bespoke code |
| Temporal / external workflow engine | Heavier ops footprint for MVP; duplicates graph semantics we need next to LLM agents |
| Fully multi-agent “supervisor swarm” as the core | Higher nondeterminism; deferred — MVP prefers explicit edges and a linear implementation path |
