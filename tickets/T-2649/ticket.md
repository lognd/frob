---
id: T-2649
title: 'post-land sweep regression from T-2629: 1 new (rule, file) identit(ies), 0
  finding(s) (F401)'
state: dropped
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/__init__.py
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
The deferred post-land unscoped sweep (T-1684) for T-2629 at commit f94e4c6d0df1a2898b8b3e1e15026fc87a4687bb found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 0 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- F401  /home/logan/projects/frob/src/frob/app/ticket_runner/__init__.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- F401  /home/logan/projects/frob/src/frob/app/ticket_runner/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-19: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (F401 src/frob/app/ticket_runner/__init__.py) is absent from a full unscoped `frob check --json` run that completed with no budget deferral and no failed/silent tool stage at T-2626's deferred sweep (T-2521: this drop only fires when that measurement itself completed -- no budget deferral, no failed/silent tool stage -- never on an unmeasured or partial run), i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
