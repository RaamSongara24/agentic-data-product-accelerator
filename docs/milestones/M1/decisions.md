# M1 decisions

| ID | Decision | Rationale |
| --- | --- | --- |
| D1 | Lightweight SQL migrations (`schema_migrations` + ordered `.sql` files), not Alembic | Sufficient for M1 table set; lower ceremony; Alembic can be adopted later if migration complexity grows |
| D2 | Dev-only APIs under `/dev/...` | Prove store without introducing production run/HITL contracts reserved for M2 |
| D3 | Payload validation keyed by `artefact_type` before persistence | Guarantees typed contracts; API returns 422 for bad payloads before run lookup side-effects confuse clients |
| D4 | Plain `str` columns for enum values; `_as_str()` treats `Enum` before `str` | `StrEnum` is a `str` subclass — naive `isinstance(..., str)` left enum members unbound incorrectly for asyncpg |
| D5 | Flush parent rows before dependent audit inserts | No ORM relationships yet; flush order otherwise violated FKs on `audit_events` |
| D6 | Stable `artefact_id` per (run, type); version increments | Matches versioning/lineage model in ADR 002 / architecture §5–6 |
| D7 | Initial field sets are intentionally lean | Formal enough for validation and store round-trips; agents will deepen payloads in later milestones |
