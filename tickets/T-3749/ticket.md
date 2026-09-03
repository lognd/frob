---
id: T-3749
title: win32 xdist suite exceeds the 3000s total-budget cap; raise win32 budgets now
  that xdist is confirmed safe
state: done
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
evidence:
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_sets_frob_test_midrun_watchdog_seconds
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

frob:waive BUG002 reason="this ticket raises two CI wall-clock budget constants (a numeric env var + a pwsh Wait-Process timeout) in ci.yml's win32 Test step, not code with a wired caller path a test can exercise before/after. The bound evidence asserts the workflow's declared budget window (midrun watchdog stays inside it); the real effect -- the parallel win32 suite completing instead of being cut off at 3000s -- is only observable in a live windows-latest CI run, not reproducible in this repo's own suite. Same spirit as T-3740/T-3746/T-3747/T-3741's BUG002 waives for the sibling CI-config changes."