---
id: T-1901
title: 'post-land sweep regression from T-1892: 1 new error(s) (SYS004)'
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
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1892 at commit c8e50a3d878dad4f2de2634ae2ebd3b41235fbb1 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- SYS004  design/frob.strata

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- SYS004  design/frob.strata  -> attributed to T-1892 (commit c8e50a3d878d, already closed/dropped -- filed below) via design/frob.strata::frob.claude_hooks

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.