---
id: T-3746
title: win32 midrun watchdog (180s) false-trips on legitimately-slow single tests;
  raise above max per-test timeout
state: queued
kind: bug
origin: human
created: '2026-09-03'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .github/workflows/ci.yml
  reason: raise win32 midrun watchdog threshold in the Test step env + update the
    matrix assertion
  actor: logan
  at: '2026-09-03'
- op: add
  glob: tests/test_ci_workflow_matrix.py
  reason: raise win32 midrun watchdog threshold in the Test step env + update the
    matrix assertion
  actor: logan
  at: '2026-09-03'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
