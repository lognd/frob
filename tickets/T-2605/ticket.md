---
id: T-2605
title: 'post-land sweep regression from T-2587: 1 new (rule, file) identit(ies), 0
  finding(s) (E501)'
state: queued
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/scaffold/project.py
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
The deferred post-land unscoped sweep (T-1684) for T-2587 at commit 44ef4f91d2ad8af95cbd05971ae89819475bb85f found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 0 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- E501  /home/logan/projects/frob/src/frob/scaffold/project.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E501  /home/logan/projects/frob/src/frob/scaffold/project.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.