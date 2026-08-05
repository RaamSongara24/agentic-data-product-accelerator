# M6 — Known limitations

1. **No live Databricks deploy** — export produces files/stubs only; job scheduling and workspace writes are deferred.
2. **Single adapter** — Databricks only; Fabric / Snowflake / Power BI remain future work.
3. **Discovery remains fixture-first** — fail-closed ACL is enforced on fixtures; live Unity Catalog passthrough is not implemented.
4. **No adapter HTTP API** — export is a library boundary callable from tests/tools; UI wiring is optional later. *(Addressed in M7: `POST /runs/{id}/export` + UI.)*
5. **No M7 demo script / DoD walkthrough** — orchestrator asks PO before M7. *(Closed in M7.)*
