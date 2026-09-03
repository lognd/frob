---
id: T-3563
title: 'post-land sweep regression from T-3560: 1 new (rule, file) identit(ies), 1
  finding(s) (unresolved-attribute)'
state: dropped
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
- tests/conftest.py
findings:
- - unresolved-attribute
  - tests/conftest.py
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
The deferred post-land unscoped sweep (T-1684) for T-3560 at commit aa92ae49ab8f9212505bc562ddda5a8840f5f810 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- unresolved-attribute  tests/conftest.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- unresolved-attribute  tests/conftest.py  -> attributed to T-3560 (commit aa92ae49ab8f, already closed/dropped -- filed below) via tests/conftest.py::_install_sigbreak_faulthandler

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-31: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (unresolved-attribute tests/conftest.py) is absent from a direct re-check of exactly the 727 named (rule, file) identit(ies) (not a full sweep) that completed with no failed/silent tool stage at doable's deferred sweep (T-2521: this drop only fires when that measurement itself completed -- no budget deferral, no failed/silent tool stage -- never on an unmeasured or partial run), i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
