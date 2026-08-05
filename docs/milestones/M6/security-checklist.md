# M6 — Security review checklist

Use this checklist when extending discovery or adapters. Evidence for M6 is linked below.

| # | Check | Expected | M6 evidence |
| --- | --- | --- | --- |
| S1 | No elevated discovery path | Discovery uses authenticated user context only; no shared admin principal | `discover_accessible_objects` raises without context; runner does not invent `"consultant"` |
| S2 | Discovery without user context fails closed | Empty / missing context → error; never full catalogue | `tests/unit/test_discovery_acl.py` |
| S3 | Explicit allow-list cannot elevate | `accessible_object_ids` intersects ACL only | Existing ACL tests + S2 suite |
| S4 | Inaccessible objects never returned | Restricted fixture objects absent for consultant | `INACCESSIBLE_OBJECT_IDS` assertions |
| S5 | Generators do not invent unseen sources | Adapter export uses only provided artefact payloads | `test_export_derives_only_from_provided_artefacts` |
| S6 | `governance_metadata` propagated | Labels/classifications copied into export assets when present | Manifest / tables / metric_view include governance; frozen fixture carries `commercial` / `internal` |
| S7 | Adapters do not elevate source permissions | Export is local stub; no platform credentials required | `deploy: false` in manifest; no deploy APIs |
| S8 | Secrets never in graph state / audit plaintext | Unchanged; LLM keys remain env-only | Config profile + settings (prior milestones) |

## Negative path (required)

```python
discover_accessible_objects(None)  # raises DiscoveryPermissionError
```

Mapping discovery with missing `user_id` in graph state likewise raises and is logged with `error_code=discovery_user_context_required`.
