---
id: T-1839
title: 'post-land sweep regression from T-1787: 1 new error(s) (SEC110)'
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
- .claude/hooks/dispatch-telemetry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1787 at commit 0ffcc39d0ec5c1882a8172ee6480e738c34248b1 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- SEC110  .claude/hooks/dispatch-telemetry.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- SEC110  .claude/hooks/dispatch-telemetry.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.