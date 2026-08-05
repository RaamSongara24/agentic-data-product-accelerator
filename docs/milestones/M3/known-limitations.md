# M3 — Known limitations

1. **Deterministic Requirements Agent by default** — live LLM quality not exercised in CI; OpenAI-compatible path is optional and untested against a live vendor.
2. **Fixture-only discovery** — no live Unity Catalog / Databricks connector.
3. **No M4 artefacts** — Semantic Model, Pipeline Spec, Metric Definitions, Review Package agents not started.
4. **No UI** — API-only consultant path.
5. **Single compiled graph** — mapping packaged as nodes/helpers rather than a separately compiled LangGraph subgraph object (behaviourally equivalent; packaging polish deferred).
6. **Test hooks** (`force_judge_outcome`, `force_empty_mapping_sources`) exist only on graph state for unit/isolation use — not exposed on the public create-run API.
