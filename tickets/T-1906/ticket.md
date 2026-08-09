---
id: T-1906
title: 'post-land sweep regression from T-1900: 1 new error(s) (invalid-argument-type)'
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
- tests/unit/gates/test_sys_interface_canonical_order.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1900 at commit 89cf432c34fcbf97cf8801cdf6b0ed3cc838de1b found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- invalid-argument-type  tests/unit/gates/test_sys_interface_canonical_order.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- invalid-argument-type  tests/unit/gates/test_sys_interface_canonical_order.py  -> attributed to T-1900 (commit 89cf432c34fc, already closed/dropped -- filed below) via tests/unit/gates/test_sys_interface_canonical_order.py::TestSysInterfaceCanonicalOrder

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.