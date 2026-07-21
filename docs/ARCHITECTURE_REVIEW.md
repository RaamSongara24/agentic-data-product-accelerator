# Architecture Review — Agentic Data Product Accelerator

| Field | Value |
| --- | --- |
| **Reviewed documents** | [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) (v1.3) |
| **Reviewer role** | Principal Software Architect |
| **Original review** | 2026-07-20 |
| **Revision** | 2026-07-20 (v1.1) — reconciled with accepted product decisions |
| **Companion docs** | [`ARCHITECTURE.md`](ARCHITECTURE.md), [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) |
| **Overall readiness** | **Ready to proceed to technical architecture and incremental implementation** — product decisions locked; remaining items are engineering design choices |

---

## 1. Executive summary

Product vision and key design decisions are now resolved in `PRODUCT_SPEC.md` v1.3. The earlier conditional readiness verdict no longer applies to those product topics.

**Resolved at product level:** consultant-first MVP, lightweight UI, per-artefact HITL semantics (Approve / Reject / Request revisions), seven canonical artefacts, technology-agnostic design with Databricks as first adapter, PostgreSQL persistence + storage abstraction, and source-platform security (no application RBAC for MVP).

**Still open:** engineering choices that belong in technical design and implementation (artefact JSON schemas, LLM provider, IdP protocol, worker topology, eval harness, etc.). These do not block starting architecture and scaffolding; they should be decided during early milestones in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

Recommendations to introduce **application-level RBAC for MVP** are **withdrawn** — they conflict with the accepted identity model.

---

## 2. Decision status board

| Topic | Prior finding | Status | Resolution |
| --- | --- | --- | --- |
| Primary MVP user | Open (Q1) | **Resolved** | Data Consultant; Business User is long-term |
| UI scope | Open (Q2, M9) | **Resolved** | Lightweight UI: submit, progress, review, approve |
| HITL semantics | Ambiguous (M8, Q10–11) | **Resolved** | Per-artefact review; Approve → next; Reject → terminate; Request revisions → regenerate current artefact & re-review |
| Canonical artefacts | Missing contracts (M3) | **Resolved (product)** | Seven named artefacts with definitions; JSON/Pydantic schemas remain an engineering task |
| Persistence | Missing (M1, Q18) | **Resolved** | PostgreSQL app DB + LangGraph checkpointer; artefacts/metadata/audit in Postgres; storage abstraction for future object storage |
| Application RBAC | Flagged as MVP gap | **Resolved — not required** | Source-platform identity/permissions; no configurable app roles for MVP |
| Platform strategy | Vendor leakage risk (R7) | **Resolved** | Technology agnostic; Databricks first for availability; adapters for platform outputs |
| Pipeline vs code | Ambiguous | **Resolved** | Canonical Pipeline Specification; adapters materialise platform assets |
| P1 workflow config | Overscoped (R6) | **Resolved (product)** | Runtime/config profile for fixed graph — not a workflow designer |
| Regeneration mechanics | — | **Deferred to architecture** | Spec intentionally omits implementation detail |

---

## 3. Findings update

### 3.1 Previously critical gaps — status

| ID | Finding | Status | Notes |
| --- | --- | --- | --- |
| M1 | Persistence undefined | **Resolved** | PostgreSQL + checkpointer + abstraction in spec |
| M2 | App identity/RBAC matrix | **Superseded** | App RBAC not MVP; source-platform enforcement required instead. IdP *protocol* still an engineering choice |
| M3 | Artefact schemas | **Partially open** | Product definitions complete; typed schemas in code still required |
| M8 | Rework/reject semantics | **Resolved (product)** | Reject terminates; Request revisions regenerates current artefact. Graph mechanics → architecture |
| M9 | UI vs API | **Resolved** | Lightweight UI mandatory for listed capabilities |

### 3.2 Risks still relevant (engineering)

| ID | Risk | Disposition |
| --- | --- | --- |
| R1 | Over-coupled long graph | Mitigate in architecture via subgraphs + artefact handoffs |
| R2 | Unbounded judge loops | Cap retries; escalate to HITL — implement in architecture |
| R4 | Supervisor complexity | Prefer linear implementation path for MVP |
| R5 | State explosion | Artefact store + IDs in graph state (aligns with Postgres strategy) |
| R9 | Timeline pressure | Manage via incremental milestones in implementation plan |

### 3.3 Withdrawn recommendations

- ~~Promote minimal application RBAC (submitter/reviewer/governance/operator) into MVP~~  
- ~~Treat five personas as requiring an in-app permissions engine~~  
- ~~Block coding until application roles are agreed~~  

Source-platform permission respect and governance-metadata propagation remain mandatory whenever external data is accessed.

---

## 4. Remaining open architectural questions

Only items that still need **technical** decisions (not product direction):

### Must decide in early implementation milestones

1. **Artefact schema formalisation** — Pydantic/JSON Schema for each of the seven canonical artefacts (fields, versioning, governance-metadata slots).  
2. **Business Requirement intake template** — concrete form fields / example payload for consultant submission.  
3. **LLM provider & secrets** — vendor, model tier, credential storage, data residency.  
4. **Authentication mechanism** — how the user authenticates to the app and how credentials/tokens are passed to Databricks/Unity Catalog (or fixtures) without elevation.  
5. **Source discovery for first demo** — fixture/upload vs live Unity Catalog under user identity (both allowed; pick for Milestone 1–2).  
6. **API + worker topology** — in-process LangGraph vs FastAPI + background worker for long runs.  
7. **Observability sink for P2/P3** — in-app event store vs LangSmith (or both).  
8. **Agent-loop caps** — numeric limits and escalation behaviour for Mapping Judge / validation retries.  
9. **Databricks adapter depth for MVP demo** — stub/export-only vs optional materialisation after Review Package approval (deploy still non-blocking for MVP acceptance).

### Can follow first vertical slice

10. G1 checklist content (manual policy pack).  
11. Retention/PII redaction for traces and schemas.  
12. Concurrent-run limits and cost budgets.  
13. Exact September demo script and calendar cut-off date.

---

## 5. Prioritised recommendations (revised)

### Still apply

1. Formalise **canonical artefact schemas** as the first domain deliverable.  
2. Implement **run lifecycle + HITL API** matching Approve / Reject / Request revisions.  
3. Use **PostgreSQL checkpointer** and artefact storage abstraction from day one.  
4. Keep agents on **canonical artefacts only**; Databricks behind an adapter interface.  
5. Cap internal agent loops; surface failures to HITL.  
6. Prefer a **linear implementation path** over a complex supervisor for MVP.  
7. Pass **user-scoped credentials** into discovery; never elevate.  
8. Deliver incrementally per [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md).

### No longer apply

- Application-level RBAC for MVP  
- Free-form Databricks code generation as the primary agent output  
- Workflow designer for P1  

---

## 6. Readiness assessment (revised)

| Dimension | Score | Comment |
| --- | --- | --- |
| Product intent & MoSCoW | **Strong** | Consultant-first, clear MVP boundary |
| Canonical model | **Strong** | Seven artefacts defined at product level |
| HITL semantics | **Strong** | Approve / Reject / Request revisions clarified |
| Persistence strategy | **Strong** | PostgreSQL + abstraction agreed |
| Security model | **Strong (product)** | Source-platform enforcement; app RBAC deferred intentionally |
| Engineering completeness | **In progress** | See [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Delivery realism | **Manageable** | Incremental plan required |

### Verdict

**Product specification is ready to guide technical architecture.**  

Proceed with [`ARCHITECTURE.md`](ARCHITECTURE.md) and [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md). Resolve remaining open questions during early milestones without reopening product decisions above.

---

## 7. Document history

| Version | Notes |
| --- | --- |
| 1.0 | Initial principal architect review of `PRODUCT_SPEC.md` v1.0 |
| 1.1 | Reconciled with accepted decisions in `PRODUCT_SPEC.md` v1.3; marked resolved items; withdrew MVP application-RBAC recommendation; retained genuine technical open questions |
