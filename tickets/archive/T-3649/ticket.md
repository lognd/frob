---
id: T-3649
title: 'post-land sweep regression from T-3648: 1 new (rule, file) identit(ies), 1
  finding(s) (COV001)'
state: done
kind: bug
origin: agent
created: '2026-09-01'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/process/_guard.py
- docs/modules/process.md
findings:
- - COV001
  - src/frob/process/_guard.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/process.md
  reason: documenting FROB_WIN32_SPAWN_DEBUG resolves the ENV001/COV001 finding this
    ticket was filed for
  actor: logan
  at: '2026-09-01'
body_changes:
- mode: append
  reason: 'mark as no-behavior-change: doc-only fix'
  actor: logan
  at: '2026-09-01'
  old_length: 1204
  new_length: 1580
evidence:
- tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_enabled_spawns_and_returns_ok
- tests/unit/test_process_guard.py::TestWin32IsolateConsoleGroup::test_sets_new_process_group_on_win32
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-3648 at commit 71e01199a1f756bceac2458d58d319cfc2c77343 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- COV001  src/frob/process/_guard.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  src/frob/process/_guard.py  -> attributed to T-3648 (commit 71e01199a1f7, already closed/dropped -- filed below) via src/frob/process/_guard.py::FROB_WIN32_SPAWN_DEBUG_ENV

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.


frob:no-behavior-change reason="pure documentation fix -- adds a missing frob:doc anchor and a doc paragraph naming FROB_WIN32_SPAWN_DEBUG; guarded_subprocess_run and _win32_isolate_console_group runtime behavior is byte-for-byte unchanged, confirmed by the full pre-existing test_process_guard.py suite (31/31) staying green with no test additions or modifications needed"