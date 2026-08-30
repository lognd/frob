---
id: T-3482
title: 'CI: macOS Test budget 25m kills the grown suite at 67%; raise to 40m like
  ubuntu (T-3426)'
state: queued
kind: bug
origin: agent
created: '2026-08-30'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/unit/test_release_workflow_gate.py
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
MEASURED on GitHub Actions run 33308245923 (macos-latest, HEAD 355eb4468,
2026-08-30): the macOS Test step started 11:10:14, reached [ 67%] and was
killed by its own `budget=1500` (25m) watcher at ~11:38 with
test_frob_self_model.py::test_sys_gate_zero_violations on the stack --
not a hang, a budget miss: the previous two macOS runs that completed
took 24m (33298117154: 06:58 -> 07:22) and 28m (33303586303), on a suite
that has grown to 12816 tests. T-3426 raised ubuntu's step budget to 40m
(job timeout-minutes 60) for exactly this reason and left macOS at 25m.

FIX: raise the macOS `budget=1500` to 2400 (40m) in .github/workflows/ci.yml,
keeping the SIGABRT-then-KILL watcher shape, and update the T-3250/T-3426
comment blocks that state the old numbers. Leave Windows alone (advisory,
T-3425). Extend tests/unit/test_release_workflow_gate.py's
TestCiUbuntuTestBudgetRaised (T-3426) with the macOS assertion so the two
platforms cannot drift apart again. ACCEPTANCE: the next macos-latest run
completes to 100% and reports its own failure count.
