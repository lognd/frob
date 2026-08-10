---
id: T-1917
title: 'post-land sweep regression from T-1910: 1 new error(s) (TICK002)'
state: queued
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1910 at commit 5b0ca91f20f7f81c0d30aaa6a096ab3edf01dc7f found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- TICK002  tickets.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- TICK002  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.