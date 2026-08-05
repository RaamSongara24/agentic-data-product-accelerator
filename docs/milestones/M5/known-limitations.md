# M5 — Known limitations

1. **No design-system / multi-persona portal** — consultant review UI only.
2. **No live event streaming (SSE/WebSocket)** — events are polled via `GET /runs/{id}/events`.
3. **No operator config write UI** — P1 is a read-only profile endpoint; prompt/model admin UI remains Should Have.
4. **No PlatformAdapter / Databricks export** — Review Package approval is in-platform only (M6).
5. **Discovery remains fixture-first** — no live Unity Catalog connector.
