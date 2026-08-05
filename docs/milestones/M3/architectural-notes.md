# M3 — Architectural notes

M3 extends the durable HITL control plane from M2 into the first real agent path:

```text
POST /runs (BR + user_context)
  → ensure_br (ArtefactStore)
  → generate_tr (Requirements Agent + optional LLM client)
  → await_tr_review (interrupt)
  → [approve] mapping: discovery → data_mapping → judge (retry caps) → persist Data Model
  → await_mapping_review (interrupt)
  → [approve] END approved
```

Alignment with [`ARCHITECTURE.md`](../../../ARCHITECTURE.md):

- Canonical artefacts only (ADR 002) — no vendor DSL as primary output.
- Secrets via env (`LLM_API_KEY`) — never in checkpointer state.
- Discovery runs as the authenticated user context; fixture mode simulates permission filtering.
- Graph state holds refs, retry counts, and small control fields; bodies stay in ArtefactStore.

Next milestone (M4) should continue from mapping approval into modelling and implementation agents — not replace the TR/mapping HITL pattern.
