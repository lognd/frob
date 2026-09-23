---
id: T-5311
title: 'WEBSEC123-125: resource-exhaustion input-bounds'
state: in-progress
kind: feature
origin: human
created: '2026-09-22'
priority: high
blocked_by:
- T-5307
parent: T-5141
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/webapp/_websec_bounds.py
- tests/fixtures/webapp/websec1xx/bounds/**
- docs/modules/webapp-websec-bounds.md
- tests/unit/test_websec_bounds.py
- src/frob/gates/_taint_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: tests/fixtures/webapp/websec1xx/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four injection
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/fixtures/webapp/websec1xx/bounds/**
  reason: narrow shared fixture glob to a per-leaf subdirectory so the four injection
    leaves can hold concurrent leases
  actor: logan
  at: '2026-09-23'
- op: add
  glob: docs/modules/webapp-websec-bounds.md
  reason: own doc file per shared WEBSEC substrate brief
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_websec_bounds.py
  reason: unit test file for websec_bounds_findings + taint_gate extension
  actor: logan
  at: '2026-09-23'
- op: add
  glob: tests/unit/test_websec_bounds.py
  reason: unit test file for websec_bounds_findings + taint_gate extension
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_taint_gate.py
  reason: fold websec_bounds_findings into the existing taint_gate call site, same
    posture T-5307 used, no new gate registration
  actor: logan
  at: '2026-09-23'
- op: add
  glob: src/frob/gates/_taint_gate.py
  reason: fold websec_bounds_findings into the existing taint_gate call site, same
    posture T-5307 used, no new gate registration
  actor: logan
  at: '2026-09-23'
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: points
  old_value: '3'
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: milestone
  old_value: null
  new_value: 0.534.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5311
branch: t-5311
---
Unbounded input length (Pydantic/Zod/class-validator schema AST for missing max_length/maxLength/maxItems), XML entity bomb/XXE (XML-parser-instantiation AST for missing resolve_entities=False/defusedxml), JSON bomb/unbounded nesting depth (body-parser config for missing depth/size limit), unbounded recursion on user-controlled input (recursive function with no max-depth guard). Item 28 (business-logic step-skipping) is dynamic-only per the corpus -- file as a frob:tests obligation in this leaf's Done report, not a static rule. Fixture per rule id.