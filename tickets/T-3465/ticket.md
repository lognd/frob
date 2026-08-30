---
id: T-3465
title: 'SELFAUDIT001: testsuite node undeclared fs.write/exec (test_strata_core_gil.py)
  and env.read (test_worker.py)'
state: queued
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
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
found while working T-3449 (post T-3458 re-measurement).

After T-3458's fix (compiled glob cache for _via_matches), the T-3449 5-test bundle under -n 4 runs clean in 176s with zero worker crashes (was: >308s with gw3/gw4 crashes before T-3458). No further T-3449 stall/crash fix is needed.

But test_sys_gate_zero_violations now fails with 8 real SELFAUDIT001 violations against the live repo, all pre-existing and unrelated to T-3449's scope:
  - tests/unit/strata/test_strata_core_gil.py:50 capability fs.write not declared (test file added by T-3457's GIL fix)
  - tests/unit/strata/test_strata_core_gil.py:67 capability exec not declared
  - tests/unit/verify/test_worker.py:302,303,345,348,377,378 capability env.read not declared (6 sites)

These need testsuite node via-list / effect declarations added in design/frob.strata for the affected files/capabilities. Out of scope for T-3449 (whose scope is src/frob/strata/_selfconform*.py, _claims.py, _facts.py -- not design/frob.strata).