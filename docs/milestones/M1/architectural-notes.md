# M1 architectural notes

M1 implements the **domain** and **persistence** layers described in [`ARCHITECTURE.md`](../../../ARCHITECTURE.md) §5–6 and ADRs 002 / 003:

- Canonical artefacts are technology-agnostic Pydantic models.
- Agents (future) will depend on `ArtefactStore`, not SQL.
- `run_id` is the correlation key that will align with LangGraph `thread_id` in M2.
- Audit and lineage tables provide the G2/G3 persistence spine without requiring workflow execution yet.

Package layout remains reserved for later milestones (`orchestration`, `adapters`, `ui`).
