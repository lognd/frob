---
id: T-3205
title: Hardcoded-layout gates must self-report NOT_APPLICABLE off-repo
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_detector_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2391 follow-up. Instance 2 from T-2391's own body: a hardcoded-layout gate (T-2384's own example: 22 files gating on a literal "src/frob/" prefix) reports a clean zero against a project with a differently-named package, when it actually measured nothing because its own candidate set was empty by construction. This is the NOT_APPLICABLE case T-2391's acceptance[1] names, distinct from NOT_MEASURED (T-2391's shipped slice only covers the all-UNRESOLVED shape). Needs a per-gate self-declaration mechanism: a gate whose declared-surface resolver (frob.lang.declared_source_prefixes or similar) returns empty for this project should be able to mark its own ToolResult/Violations as NOT_APPLICABLE with a stated reason, distinct from a genuine "measured, zero findings" pass. Must-fire: point a layout-dependent gate at a synthetic foreign-package-name fixture project and assert its result is NOT_APPLICABLE, not a clean pass. Must-stay-quiet: the same gate against this repo's own src/frob/ layout stays a normal measured result.
