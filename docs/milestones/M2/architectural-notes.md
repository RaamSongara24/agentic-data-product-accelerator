# M2 architectural notes

M2 proves the **durable HITL control plane** described in [`ARCHITECTURE.md`](../../../ARCHITECTURE.md) §7 and ADRs 001 / 003 / 005:

```text
POST /runs
  → create workflow_runs row
  → LangGraph ainvoke (thread_id = run_id)
  → generate_stub writes Business Requirement v1 via ArtefactStore
  → await_review interrupt
  → status waiting_for_review

POST /runs/{id}/reviews
  → audit review_submitted
  → Command(resume=decision)
  → approve → approved | reject → terminated
    | request_revisions → generate_stub (vN+1) → interrupt again
```

- Graph state holds **refs and control fields** only; artefact JSON lives in PostgreSQL via ArtefactStore.
- Checkpointer tables are owned by LangGraph; application tables remain the source for artefact versioning, audit, and lineage.
- Restart durability: a new API process re-opens the same checkpointer pool and resumes an interrupted thread by `run_id`.

Next milestone (M3) should extend this graph with a real Requirements path and mapping subgraph — not replace the HITL/checkpointer pattern.
