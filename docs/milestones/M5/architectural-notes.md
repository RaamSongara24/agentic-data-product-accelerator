# M5 architectural notes

M5 adds a thin presentation layer over the M4 control plane:

```text
Browser (/ui/)
  → POST /runs                    (Business Requirement + user_context)
  → GET  /runs/{id}               (status + pending_review)
  → GET  /runs/{id}/artefacts…    (list + payload for viewer)
  → POST /runs/{id}/reviews       (approve | reject | request_revisions)
  → GET  /runs/{id}/events        (audit / operator traces)
  → GET  /config/profile          (runtime profile for fixed graph)
```

- The LangGraph seven-artefact path is unchanged; the UI does not bypass HITL.
- Artefact JSON remains in PostgreSQL via ArtefactStore; graph state holds refs only.
- Config profile is **runtime selection for one fixed compiled graph** — not a workflow designer (ADR 001 / product P1).

Next milestone (M6) should introduce the adapter boundary — not expand the UI into a full product portal.
