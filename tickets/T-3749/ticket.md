---
id: T-3749
title: win32 xdist suite exceeds the 3000s total-budget cap; raise win32 budgets now
  that xdist is confirmed safe
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .github/workflows/ci.yml
  reason: raise win32 FROB_TEST_TOTAL_BUDGET_SECONDS + Wait-Process budget; xdist
    confirmed safe (run 33804740730 showed workers running, no saga, just slow)
  actor: logan
  at: '2026-09-03'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
