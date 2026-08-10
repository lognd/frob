---
id: T-1919
title: 'post-land sweep regression from T-1867: 2 new error(s) (DOC007, DRIFT002)'
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_mutate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_anchor_cli.py::TestAnchorCli::test_set_anchor_via_cli
- tests/unit/test_ticket_anchor_cli.py::TestAnchorCli::test_clear_anchor_via_cli
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1867 at commit 1fe11d69dc4514dcd37d33ac43a54cb1bb19aa81 found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- DOC007  src/frob/app/ticket_runner/_mutate.py
- DRIFT002  src/frob/app/ticket_runner/_mutate.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC007  src/frob/app/ticket_runner/_mutate.py  -> attributed to T-1867 (commit 1fe11d69dc45, already closed/dropped -- filed below) via src/frob/app/ticket_runner/__init__.py::_ticket_dispatch_table -> src/frob/app/ticket_runner/_mutate.py::_runs_last
- DRIFT002  src/frob/app/ticket_runner/_mutate.py  -> attributed to T-1867 (commit 1fe11d69dc45, already closed/dropped -- filed below) via src/frob/app/ticket_runner/__init__.py::_ticket_dispatch_table -> src/frob/app/ticket_runner/_mutate.py::_runs_last

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.