# M3 — Decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D1 | Deterministic LLM provider default; optional OpenAI-compatible client via env | CI/golden tests need no API key; vendor choice remains open (ARCHITECTURE open Q) |
| D2 | No BR HITL — consultant-authored intake only | M3 deliverables call out HITL after TR and after mapping; BR is submission artefact |
| D3 | Mapping review artefact = Data Model slice with `mapping_context` | Matches architecture “mapping/data-model slice”; reuses M1 schema |
| D4 | Fixture ACL ∩ optional allow-list (never elevates) | Source-platform least privilege; explicit ids cannot unlock restricted fixtures |
| D5 | Mapping Judge retry caps via settings (`MAPPING_*_RETRY_CAP`, default 2) | ARCHITECTURE §7.3; escalates to HITL with notes when exhausted |
| D6 | M3 exit = approve mapping → `approved` (no M4 nodes) | Scope control; orchestrator gates M4 |
