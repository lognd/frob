---
id: T-3679
title: 'post-land sweep regression from T-3675: 2 new (rule, file) identit(ies), 2
  finding(s) (COV001, PERF004)'
state: dropped
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
- src/frob/check/__init__.py
- src/frob/refactor/_scan_carry.py
findings:
- - COV001
  - src/frob/check/__init__.py
- - PERF004
  - src/frob/refactor/_scan_carry.py
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
The deferred post-land unscoped sweep (T-1684) for T-3675 at commit b50778e45ad9710267f9960d59088f54a8118045 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- COV001  src/frob/check/__init__.py
- PERF004  src/frob/refactor/_scan_carry.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  src/frob/check/__init__.py  -> attributed to T-3675 (commit b50778e45ad9, already closed/dropped -- filed below) via src/frob/check/__init__.py::FROB_CHECK_STOP_BEFORE_ENV
- PERF004  src/frob/refactor/_scan_carry.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-09-02: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (COV001 src/frob/check/__init__.py, PERF004 src/frob/refactor/_scan_carry.py) is absent from a direct re-check of exactly the 764 named (rule, file) identit(ies) (not a full sweep) that completed with no failed/silent tool stage at doable's deferred sweep (T-2521: this drop only fires when that measurement itself completed -- no budget deferral, no failed/silent tool stage -- never on an unmeasured or partial run), i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
