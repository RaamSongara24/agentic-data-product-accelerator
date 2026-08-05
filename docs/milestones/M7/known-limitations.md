# M7 — Known limitations

1. **No live Databricks deploy** — export remains a file/stub bundle (`mode=export_stub`).
2. **Discovery remains fixture-first** — ACL fail-closed is demonstrated on fixtures; live Unity Catalog token passthrough is post-MVP.
3. **No application RBAC / multi-persona portal** — consultant-led thin UI only (PRODUCT_SPEC non-goal).
4. **No visual workflow designer** — P1 is runtime/config for a fixed LangGraph.
5. **Screenshots optional** — demo is script-driven; capture screenshots during stakeholder dry-run if needed and drop under `docs/milestones/M7/screenshots/`.

These are intentional residual gaps owned by the orchestrator / post-MVP backlog — not §14.1 failures.
