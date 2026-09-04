---
id: T-3750
title: T-3748/T-3749 ci.yml changes broke 4 workflow-assertion tests (job timeout
  ceiling, ubuntu-step regex, mac/ubuntu budget parity)
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
- tests/test_ci_workflow_timeout.py
- tests/unit/test_release_workflow_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_ci_workflow_timeout.py
  reason: update the 4 workflow-assertion tests to match T-3748/T-3749's new ci.yml
    (job timeout 150, ubuntu step runs frob coverage --full --fail-on-degraded, mac/ubuntu
    budgets intentionally diverge)
  actor: logan
  at: '2026-09-03'
- op: add
  glob: tests/unit/test_release_workflow_gate.py
  reason: update the 4 workflow-assertion tests to match T-3748/T-3749's new ci.yml
    (job timeout 150, ubuntu step runs frob coverage --full --fail-on-degraded, mac/ubuntu
    budgets intentionally diverge)
  actor: logan
  at: '2026-09-03'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
