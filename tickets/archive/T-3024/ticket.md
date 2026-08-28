---
id: T-3024
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3007):
  1 new (rule, file) identit(ies), 1 finding(s) (DOC006)'
state: dropped
kind: bug
origin: agent
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-3022/ticket.md
findings:
- - DOC006
  - tickets/T-3022/ticket.md
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3007) at commit c233006aba7377b782db82bfde3bfa83476d13bd found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  tickets/T-3022/ticket.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  tickets/T-3022/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-27: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (DOC006 tickets/T-3022/ticket.md) is absent from a full unscoped `frob check --json` run that completed with no budget deferral and no failed/silent tool stage at T-3119's deferred sweep (T-2521: this drop only fires when that measurement itself completed -- no budget deferral, no failed/silent tool stage -- never on an unmeasured or partial run), i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
