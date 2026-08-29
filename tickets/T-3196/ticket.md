---
id: T-3196
title: 'post-land sweep regression from T-2710: 2 new (rule, file) identit(ies) (DRIFT001,
  SYS003)'
state: done
kind: bug
origin: agent
created: '2026-08-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
- src/frob/gates/__init__.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_gates.py::TestDriftGate::test_no_drift_when_clean
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
findings:
- - DRIFT001
  - src/frob/gates/__init__.py
- - SYS003
  - src/frob/check/_python.py
---
The deferred post-land unscoped sweep (T-1684) for T-2710 at commit 69fa1b0d9f94d7c99502ac70b9d069688bd9d93a found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- DRIFT001  src/frob/gates/__init__.py
- SYS003  src/frob/check/_python.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DRIFT001  src/frob/gates/__init__.py  -> attributed to T-2710 (commit 69fa1b0d9f94, already closed/dropped -- filed below) via src/frob/gates/__init__.py::_load_graph_queue_lock -> src/frob/gates/__init__.py::_require -> src/frob/gates/__init__.py::_T
- SYS003  src/frob/check/_python.py  -> attributed to T-2710 (commit 69fa1b0d9f94, already closed/dropped -- filed below) via src/frob/check/_python.py::_gates_error_result

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.