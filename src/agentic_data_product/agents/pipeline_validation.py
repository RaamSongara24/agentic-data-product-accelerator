"""Static validation for Pipeline Specification (no code execution)."""

from __future__ import annotations

from agentic_data_product.domain.artefacts import PipelineSpecificationPayload


def validate_pipeline_specification(
    pipeline: PipelineSpecificationPayload,
) -> list[str]:
    """Return human-readable validation results (pass and fail notes).

    Checks are deterministic and side-effect free: stage identity, dependency
    references, cycle detection, and basic structural completeness.
    """
    results: list[str] = []
    names = [s.name for s in pipeline.stages]

    if not pipeline.stages:
        results.append("FAIL: Pipeline Specification has no stages")
        return results

    results.append(f"PASS: Pipeline has {len(pipeline.stages)} stage(s)")

    if len(names) != len(set(names)):
        results.append("FAIL: Duplicate stage names detected")
    else:
        results.append("PASS: Stage names are unique")

    name_set = set(names)
    for stage in pipeline.stages:
        for dep in stage.dependencies:
            if dep not in name_set:
                results.append(f"FAIL: Stage '{stage.name}' depends on unknown stage '{dep}'")
            elif dep == stage.name:
                results.append(f"FAIL: Stage '{stage.name}' depends on itself")

    # Cycle detection via DFS
    graph = {s.name: list(s.dependencies) for s in pipeline.stages}
    visiting: set[str] = set()
    visited: set[str] = set()

    def _dfs(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for nxt in graph.get(node, []):
            if nxt in graph and _dfs(nxt):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    cyclic = any(_dfs(n) for n in graph)
    if cyclic:
        results.append("FAIL: Dependency cycle detected among stages")
    else:
        results.append("PASS: No dependency cycles")

    kinds = {s.kind for s in pipeline.stages}
    if "ingest" not in kinds:
        results.append("WARN: No ingest stage present")
    else:
        results.append("PASS: Ingest stage present")
    if "validate" not in kinds:
        results.append("WARN: No validate stage present")
    else:
        results.append("PASS: Validate stage present")

    if pipeline.validation_rules:
        results.append(
            f"PASS: {len(pipeline.validation_rules)} declarative validation rule(s) declared"
        )
    else:
        results.append("WARN: No validation_rules declared on the specification")

    fail_count = sum(1 for r in results if r.startswith("FAIL:"))
    if fail_count == 0:
        results.append("PASS: Static validation completed with no failures")
    else:
        results.append(f"FAIL: Static validation completed with {fail_count} failure(s)")

    return results
