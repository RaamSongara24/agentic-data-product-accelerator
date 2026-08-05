# M4 — Known limitations

1. **No consultant UI** — review remains API-only (M5).
2. **No PlatformAdapter / Databricks export** — Review Package approval is in-platform only (M6).
3. **Pipeline Spec has no dedicated HITL interrupt** — reviewed as part of the implementation stage with Metric Definitions as the pending pointer; static validation results appear on the Review Package.
4. **LLM path is best-effort** — non-deterministic providers fall back to heuristics on parse failure.
5. **Discovery remains fixture-first** — no live Unity Catalog connector.
