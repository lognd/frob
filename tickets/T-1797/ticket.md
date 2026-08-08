---
id: T-1797
title: 'post-land sweep regression from T-1674: 2 new error(s) (ARCH103, SEC110)'
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
- src/frob/app/ticket_runner/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1674 at commit 5df3d4c629fca49f5448542e2ce077c09cdbc75a found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- ARCH103  src/frob/app/ticket_runner/__init__.py
- SEC110  src/frob/app/ticket_runner/__init__.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.