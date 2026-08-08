---
id: T-1812
title: 'post-land sweep regression from T-1735: 2 new error(s) (invalid-assignment,
  unresolved-attribute)'
state: in-progress
kind: bug
origin: agent
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_land.py
- tests/test_tickets.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1735 at commit 9f128a0b4d5658ff2ed732a1c8242f048e508d27 found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- invalid-assignment  tests/test_ticket_land.py
- unresolved-attribute  tests/test_tickets.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.