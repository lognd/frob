---
id: T-1894
title: 'post-land sweep regression from T-1880: 2 new error(s) (invalid-argument-type)'
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
- src/frob/app/ticket_runner/_lifecycle.py
- tests/test_tickets_scope_mutation.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1880 at commit c9fa9f2c620664267d82da66e91384c7a9ac3b5c found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- invalid-argument-type  src/frob/app/ticket_runner/_lifecycle.py
- invalid-argument-type  tests/test_tickets_scope_mutation.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- invalid-argument-type  src/frob/app/ticket_runner/_lifecycle.py  -> attributed to T-1880 (commit c9fa9f2c6206, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_lifecycle.py::_refuse_on_scope_lease_collision
- invalid-argument-type  tests/test_tickets_scope_mutation.py  -> attributed to T-1880 (commit c9fa9f2c6206, already closed/dropped -- filed below) via tests/test_tickets_scope_mutation.py::TestScopeLeaseConflict

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.