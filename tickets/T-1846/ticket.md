---
id: T-1846
title: 'post-land sweep regression from T-1554: 1 new error(s) (DOC001)'
state: queued
kind: bug
origin: agent
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/design/land-checkpoint-durability.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1554 at commit f9aea34a59c5a70ec70bacf887e8d1589c3d003f found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- DOC001  docs/design/land-checkpoint-durability.md

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.