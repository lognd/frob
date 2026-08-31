---
id: T-3603
title: 'post-land sweep regression from T-3600: 1 new (rule, file) identit(ies), 3
  finding(s) (DRIFT002)'
state: queued
kind: bug
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/check_runner.py
findings:
- - DRIFT002
  - src/frob/app/check_runner.py
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
The deferred post-land unscoped sweep (T-1684) for T-3600 at commit 3cb2c3de793dafd84aa102a8bed16d7547575a2a found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 3 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DRIFT002  src/frob/app/check_runner.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV003  tests/test_check_runner.py  -> attributed to T-3600 (commit 3cb2c3de793d, already closed/dropped -- filed below) via tests/test_check_runner.py::TestClaudeConfigDriftStage
- DRIFT002  src/frob/app/check_runner.py  -> attributed to T-3600 (commit 3cb2c3de793d, already closed/dropped -- filed below) via src/frob/app/check_runner.py::_claude_config_drift_result

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.