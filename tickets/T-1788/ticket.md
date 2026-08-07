---
id: T-1788
title: 'post-land sweep regression from T-1222: 2 new error(s) (PRE001, SCOPE001)'
state: queued
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- rapid-debt.jsonl
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1222 at commit 713b48b9028b7c74d8b2ef179bb0ea6393ef78fe found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- PRE001  rapid-debt.jsonl
- SCOPE001  rapid-debt.jsonl

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.