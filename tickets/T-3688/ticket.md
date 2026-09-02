---
id: T-3688
title: 'clear self-gate residue: ruff-format drift, stale T-3604 evidence, stale T-3053
  block edge'
state: queued
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_conftest_midrun_watchdog.py
- tickets/T-3604/ticket.md
- tickets/T-3053/ticket.md
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
Self-gate cleanup (AL implementer series), current measured state:

1. ruff-format warning: tests/unit/test_conftest_midrun_watchdog.py needs
   reformatting (part of a 3-file drift set; the other two files --
   src/frob/app/telemetry/_state.py and src/frob/graph/__init__.py -- are
   out of this series' scope per fleet discipline, left for their owning
   series).

2. gate:COV COV003 error: T-3604 (done) cites evidence
   tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_step_has_continue_on_error
   which no longer resolves. The test was renamed to
   test_step_has_no_continue_on_error (semantics flipped: the diag step
   must NOT carry continue-on-error). Rebind the evidence citation to the
   current test id via frob ticket evidence --replace.

3. gate:TICK TICK004 error: T-3053 (critical, epic) has sat queued 7d.
   Its blocked_by=['T-3088'] is stale -- T-3088 is done (archived). Clear
   the stale block edge with frob ticket unblock --by T-3088.
   This is the same finding T-3687 (post-land sweep residue) flagged;
   close T-3687 once this lands, citing this ticket.