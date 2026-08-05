# Must Have coverage map (PRODUCT_SPEC §7 / §14.1 item 2)

| ID | Intent (consultant-led) | Demonstrated how | Result |
| --- | --- | --- | --- |
| **U1** | Submit structured business requirements | UI form / `POST /runs` | Pass |
| **U2** | Describe needs (NL supported, not UX centrepiece) | Intent/objectives free text on structured form | Pass* |
| **U3** | Facts / dimensions / measures from requirements | Semantic Model + Metric Definitions generation | Pass |
| **U4** | Review generated semantic artefacts | HITL artefact viewer + Approve/Reject/Revisions | Pass |
| **A1** | Generate measures and dimensions | Modelling + metrics agents | Pass |
| **A3** | Validate semantic models | Review Package validation_results + HITL | Pass |
| **A4** | Review business logic / calculations | Metric Definitions HITL gate | Pass |
| **D1** | Generate pipeline specifications | Pipeline Specification artefact | Pass |
| **D2** | Review generated pipelines (canonical specs) | Implementation HITL (metrics gate after pipeline) | Pass |
| **D3** | Validate source-to-target mappings | Mapping subgraph + Data Model HITL | Pass |
| **D4** | Review transformation logic | Data Model / Pipeline Specification payloads | Pass |
| **G1** | Review for governance standards | Review Package + governance_metadata | Pass |
| **G2** | Complete audit trail | `GET /runs/{id}/events` + UI events | Pass |
| **G3** | Lineage BR → artefacts | `GET /runs/{id}/lineage` + UI lineage | Pass |
| **G4** | Review approval workflow before publish | Staged HITL; RP `decision_state=approved` | Pass |
| **P1** | Runtime/config for fixed graph | `GET /config/profile` + env settings | Pass* |
| **P2** | Monitor agent execution | Run status + events | Pass |
| **P3** | View agent interactions / decisions | Events, artefact versions, review comments | Pass |

\* Per PRODUCT_SPEC: U2 remains Must Have but MVP optimises for structured design; P1 is runtime/config for a fixed LangGraph, not a workflow designer.
