---
id: T-3428
title: 'post-land sweep regression from T-3245: 1 new (rule, file) identit(ies), 3
  finding(s) (DRIFT001)'
state: done
kind: bug
origin: agent
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
findings:
- - DRIFT001
  - src/frob/app/ticket_runner/_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record no-behavior-change front door for BUG002
  actor: logan
  at: '2026-08-29'
  old_length: 1324
  new_length: 1551
evidence:
- tests/unit/test_rapid_sweep.py::TestFileRegressionTicket::test_commit_failure_skips_auto_dispose_and_returns_none
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-3245 at commit 6febbffcef5fec6193ee707f3d50964abbe4ee8b found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 3 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py  -> attributed to T-3245 (commit 6febbffcef5f, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket -> src/frob/app/ticket_runner/_rapid_sweep.py::_attribute_new_findings

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.



frob:no-behavior-change reason="Fix is doc-only: added a paragraph to docs/modules/tickets-verify-sweep.md documenting T-3245's existing locking behavior, then re-acked _file_regression_ticket. No production logic changed."