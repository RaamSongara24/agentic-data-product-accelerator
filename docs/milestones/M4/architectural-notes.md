# M4 — Architectural notes

M4 extends the durable HITL control plane from M3 into modelling and the linear implementation path:

```text
POST /runs (BR + user_context)
  → ensure_br
  → generate_tr → await_tr_review
  → [approve] mapping subgraph → await_mapping_review
  → [approve] modelling (Semantic Model + Data Model) → await_modelling_review
  → [approve] generate_pipeline → validate_pipeline → generate_metrics
       → await_implementation_review
  → [approve] assemble_rp → await_rp_review
  → [approve] END approved
```

Alignment with [`ARCHITECTURE.md`](../../../ARCHITECTURE.md) §7:

- Canonical artefacts only (ADR 002).
- HITL decision contract: Approve / Reject / Request revisions (ADR 005).
- Implementation path is linear (no complex supervisor): Engineer → static validate → Metrics → HITL → Review Package.
- Graph state holds refs and small control fields; bodies stay in ArtefactStore.
- Secrets never in checkpointer state.

Next milestone (M5) should add a lightweight UI over the existing `/runs` APIs — not replace the graph.
