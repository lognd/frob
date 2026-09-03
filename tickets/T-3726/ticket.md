---
id: T-3726
title: 'win32: total-budget watchdog never fires + budget-var recheck'
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
- src/frob/check/**
- src/frob/process/**
- tests/conftest.py
- tests/unit/test_conftest_midrun_watchdog.py
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: .github/workflows/ci.yml
  reason: T-3725 already holds an in-progress lease on ci.yml (doctor exit-1 fix);
    this ticket's ci.yml diagnostics (budget var, TOTAL_BUDGET env) can be verified
    via git-checked-out content without an active lease, and re-added if a ci.yml
    edit is needed once T-3725 lands
  actor: logan
  at: '2026-09-03'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-3707/T-3708/T-3713. CI run 33715737237 (post T-3707/T-3708/T-3713): Windows Test step still hit the outer 1500s Wait-Process timeout with literal unexpanded dollar-budget-braces in the error message, AND FROB_TEST_TOTAL_BUDGET_SECONDS=1200 watchdog never fired (no SUITE-RESULT: TOTAL-BUDGET-EXCEEDED line), only the 180s midrun stall watchdog armed. Need to: (1) find+fix the actual unexpanded budget-var instance if any remains, or otherwise explain the discrepancy with static analysis showing it is already curly-brace form; (2) reproduce+fix why the total-budget watchdog does not fire (local repro needed: short FROB_TEST_TOTAL_BUDGET_SECONDS + a long-sleeping test run properly against this repo's own tests/conftest.py wiring); (3) investigate per-check win32 slowness (9.5s baseline, 120s FROB_DISABLE_EXEC atexit gap) and daemon-worker ThreadPoolExecutor fix in the check pipeline if evidence supports it.