---
id: T-3778
title: 'revert T-3776 --reruns: pytest-rerunfailures INTERNALERRORs under xdist on
  py3.14 macos'
state: queued
kind: bug
origin: human
created: '2026-09-04'
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
  reason: revert reruns flags
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/test_ci_workflow_matrix.py
  reason: remove rerun tests
  actor: logan
  at: '2026-09-04'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
