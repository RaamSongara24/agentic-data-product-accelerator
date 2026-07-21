# Contributing

Thank you for contributing to the **Agentic Data Product Accelerator**. This guide keeps the codebase maintainable and aligned with the agreed architecture.

**Read first:** [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md), and existing [`adr/`](adr/) records.

---

## Development philosophy

- **Canonical first** — agents produce technology-agnostic artefacts; adapters come last.  
- **Small, vertical slices** — ship runnable increments (see milestones M0–M7).  
- **HITL is product behaviour** — review decisions are first-class, not afterthoughts.  
- **No silent architecture drift** — significant deviations need an ADR.  
- **Production quality from day one** — typed models, tests for control flow, no privilege elevation.

Do not reopen settled product decisions (consultant-first MVP, no application RBAC for MVP, PostgreSQL persistence, Databricks as first adapter only). Discuss changes via ADR + product owner agreement.

---

## Branching strategy

| Branch | Purpose |
| --- | --- |
| `main` | Stable baseline; protected |
| `feature/<short-name>` | New capability or milestone work |
| `fix/<short-name>` | Bug fixes |
| `docs/<short-name>` | Documentation-only changes |

- Branch from the latest `main`.  
- Prefer one logical change per branch/PR.  
- Delete the branch after merge.

---

## Commit message conventions

Use concise, imperative subjects (≈72 chars). Optional body for *why*.

Examples:

```text
Add ArtefactStore PostgreSQL backend

Wire LangGraph Postgres checkpointer for HITL resume

fix: terminate run on HITL reject decision
```

Avoid vague messages (`update`, `wip`, `fix stuff`).

---

## Pull request expectations

Every PR should:

1. State the milestone or problem it addresses.  
2. Link related issues/ADRs when relevant.  
3. Keep scope focused — no drive-by refactors unrelated to the change.  
4. Include or update tests for behaviour changes.  
5. Update docs when contracts or developer workflows change.  
6. Pass lint, format, and test checks before review.  
7. Call out any intentional architecture trade-offs.

Reviewers verify alignment with [`ARCHITECTURE.md`](ARCHITECTURE.md) and technology-agnostic principles (below).

---

## Coding standards

- **Python 3.12+** (confirm in `pyproject.toml` once M0 lands).  
- Prefer explicit **Pydantic** models for artefacts, API payloads, and review decisions.  
- LangGraph state holds **refs and control fields**, not large artefact blobs.  
- Depend on **interfaces** (`ArtefactStore`, `PlatformAdapter`) — not vendor SDKs — inside agent nodes.  
- Propagate **authenticated user context** into source-platform tools; never elevate permissions.  
- No secrets in code, fixtures committed to git, or graph state.

### Formatting and linting

Once tooling is added in M0 (expected: Ruff and/or similar):

```bash
uv run ruff check .
uv run ruff format .
```

Follow the project config; do not disable rules without discussion.

### Testing expectations

| Change type | Expected tests |
| --- | --- |
| Domain schemas | Unit validation tests |
| Graph routing / HITL | Graph tests for Approve, Reject, Request revisions |
| Persistence | Integration tests against PostgreSQL |
| Adapters | Pure mapping tests from frozen artefact fixtures |
| API | Route tests for run lifecycle and reviews |

Prefer deterministic fixtures over live LLM/Databricks calls in CI. Live integration tests, if any, must be opt-in.

---

## Documentation expectations

- User-facing or contract changes → update `PRODUCT_SPEC.md` and/or `ARCHITECTURE.md` as appropriate (or open an ADR).  
- Milestone completion → note status in `README.md` / `IMPLEMENTATION_PLAN.md` if exit criteria change.  
- New cross-cutting decision → add an ADR under `adr/`.  
- Keep terminology consistent: **Business Requirement**, **Request revisions**, **canonical artefact**, **adapter**, **lightweight UI**.

---

## How to add a new LangGraph node

1. Place the node under `src/orchestration/` (or the package layout established in M0).  
2. Define typed inputs/outputs; write results via `ArtefactStore`, put only refs in state.  
3. Register the node in the compiled graph with explicit edges.  
4. If the node produces a canonical artefact, add a **HITL interrupt** before progression (Approve / Reject / Request revisions).  
5. Cap any internal retry loops; escalate to HITL on exhaustion.  
6. Add graph tests for success and failure paths.  
7. Emit structured run events for observability.

Do not embed Databricks (or other vendor) write calls in agent nodes.

---

## How to add a new canonical artefact

1. Confirm product need in `PRODUCT_SPEC.md` (or propose an ADR if the set of seven changes).  
2. Add a Pydantic model in `src/domain/` with versioning and optional `governance_metadata`.  
3. Extend `ArtefactStore` serialization/validation.  
4. Wire producers/consumers in the graph and lineage edges.  
5. Ensure HITL review covers the new artefact before later stages.  
6. Update adapters only if they must materialise the new type — keep agents vendor-neutral.  
7. Add schema and graph tests; update docs/ADR if the catalogue changes.

---

## How to add a new platform adapter

1. Implement `PlatformAdapter` under `src/adapters/<platform>/`.  
2. Accept **approved** canonical artefacts only; produce platform-specific outputs.  
3. Do not change upstream agent prompts/graphs to target the new platform.  
4. Add fixture-based unit tests (no live deploy required for MVP-quality contributions).  
5. Document configuration and limitations in the adapter README or `ARCHITECTURE.md`.  
6. Record non-trivial adapter strategy in an ADR if it affects shared contracts.

First reference implementation: Databricks (`adr/004-platform-adapter-architecture.md`).

---

## Maintaining technology-agnostic design

- Agents output **Pipeline Specification** and **Metric Definitions**, not notebooks or Unity Catalog DDL, as primary artefacts.  
- Vendor SDKs belong in `integrations/` (read/discovery as user) or `adapters/` (materialisation) — not in domain models.  
- Discovery must respect source-platform RBAC using the authenticated user.  
- Prefer portable fields in artefacts; put platform hints in adapter config, not in the canonical core.

---

## Preserving architectural consistency

| Do | Don't |
| --- | --- |
| Follow ADRs and `ARCHITECTURE.md` | Bypass the ArtefactStore with ad-hoc SQL in nodes |
| Use PostgreSQL checkpointer for HITL | Fake HITL with in-memory-only state in shared environments |
| Keep one fixed graph + config profiles | Build a workflow designer for MVP |
| Terminate on Reject; revise current artefact only | Silently restart the entire run on Request revisions |
| Add tests with behaviour changes | Land untested graph edge changes |

When unsure, open a draft ADR before a large PR.

---

## Getting help

- Product questions → `PRODUCT_SPEC.md` / Technical Product Lead  
- Design questions → `ARCHITECTURE.md` / ADRs  
- Delivery sequencing → `IMPLEMENTATION_PLAN.md`
