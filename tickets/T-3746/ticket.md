---
id: T-3746
title: win32 midrun watchdog (180s) false-trips on legitimately-slow single tests;
  raise above max per-test timeout
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
evidence:
- tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_sets_frob_test_midrun_watchdog_seconds
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

frob:waive BUG002 reason="this ticket raises a CI watchdog threshold (a numeric constant in ci.yml's win32 Test step env), not a code defect with a wired caller path a test can exercise before/after. The bound evidence asserts the workflow's declared threshold stays within the step's Wait-Process budget, which holds both before and after by construction. The real defect -- the 180s midrun watchdog false-firing on legitimately-slow single tests -- is only observable in a live win32 CI run against slow real subprocesses, not reproducible in this repo's own suite. Same spirit as T-3740's BUG002 waive for the sibling budget change."