---
id: T-3687
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3686):
  1 new (rule, file) identit(ies), 1 finding(s) (TICK004)'
state: dropped
kind: bug
origin: agent
created: '2026-09-02'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets.md
findings:
- - TICK004
  - tickets.md
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3686) at commit 4a1fafe54ee9c9f051fb981164820e10a696e71e found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- TICK004  tickets.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-09-02: the TICK004 finding this sweep filed was genuine (T-3053's stale blocked_by=T-3088 edge + critical-priority rot) and is now fixed by T-3688: T-3088's edge cleared and T-3053 reprioritized to high. Not stale residue -- absorbed into T-3688's fix. (absorbed by T-3688)
