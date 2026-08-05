# M7 — Decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D1 | Persist RP `decision_state=approved` on final HITL Approve | Adapter gate and “in-platform publish” require artefact-level approval, not only run status |
| D2 | Add production `GET /runs/{id}/lineage` | G3 demo without relying on `/dev` APIs |
| D3 | Add `POST /runs/{id}/export` as optional stub | Makes M6 adapter demonstrable to newcomers; still no live deploy |
| D4 | Surface lineage + export in thin UI | Stakeholder walkthrough without raw clients; export disabled until approved |
| D5 | Keep PRODUCT_SPEC text unchanged | Delivered behaviour already matches §14.1; evidence lives in M7 docs |
| D6 | Escalate residual gaps (live UC, live deploy) explicitly | Do not paper over non-goals as DoD failures |
