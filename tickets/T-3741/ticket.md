---
id: T-3741
title: re-enable xdist on the win32 CI Test step now that the subprocess-hang root
  causes are fixed
state: queued
kind: feature
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
  reason: remove -p no:xdist from the win32 Test step to re-enable parallel xdist;
    update any matrix assertion
  actor: logan
  at: '2026-09-03'
- op: add
  glob: tests/test_ci_workflow_matrix.py
  reason: remove -p no:xdist from the win32 Test step to re-enable parallel xdist;
    update any matrix assertion
  actor: logan
  at: '2026-09-03'
body_changes:
- mode: set
  reason: add description and plan for xdist re-enable follow-up
  actor: logan
  at: '2026-09-03'
  old_length: 0
  new_length: 1190
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

The win32 `Test (windows, timed with hang guard)` CI step runs pytest with
`-p no:xdist` (single-threaded), a leftover from the hang-diagnostics era
(T-3675/T-3683/T-3689/T-3692/T-3707). The hang root causes that motivated
disabling xdist there are all fixed:

- T-3686: self-inflicted `os.kill`/Ctrl-C interrupt
- T-3708: abandoned-thread atexit wedge
- T-3726: capture-related hang
- T-3730/T-3735: test_cli_doctor hangs
- T-3738: test_wire hang

`FROB_TEST_IGNORE_CONSOLE_CTRL=1` (already set on this step) mitigates
console signal delivery. With those causes fixed, running serially is no
longer buying diagnostic safety, only cost: ~50 minutes of wall-clock for
the win32 leg (see T-3740, which raised the budgets to let this already-
completing serial suite finish rather than timing out).

## Plan

Restore `-n auto` (or the equivalent xdist invocation used on ubuntu/mac) to
the win32 Test step's pytest invocation, matching the other matrix legs, and
re-tighten the wall-clock budgets T-3740 raised back down to something
appropriate for a parallel run once xdist is confirmed stable there again.

Leave in the backlog -- do not work this ticket as part of T-3740.
