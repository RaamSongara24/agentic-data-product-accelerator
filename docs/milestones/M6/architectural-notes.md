# M6 architectural notes

M6 introduces the platform materialisation boundary outside the agent graph:

```text
Approved CanonicalArtefacts
        │
        ▼
 PlatformAdapter.to_platform(artefacts, target_config) -> AdapterResult
        │
        └── DatabricksAdapter  (export_stub: YAML / JSON / notebooks-as-files)
```

- Agents continue to produce technology-agnostic artefacts only.
- Adapter inputs must include an **approved** Review Package; unapproved packages raise `AdapterApprovalRequiredError`.
- Governance metadata from envelopes (and attribute-level notes where present) is copied into export assets.
- Discovery remains an **integration** concern (read-as-user), not adapter materialisation — and fails closed without user context.

```text
POST /runs (BR + user_context)
  → … seven-artefact HITL …
  → Review Package approved
  → (optional) DatabricksAdapter.to_platform(approved artefacts)
```

Next milestone (M7) is MVP demonstration / DoD — not additional adapters or live deploy.
