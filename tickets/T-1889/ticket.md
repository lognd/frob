---
id: T-1889
title: 'post-land sweep regression from T-1885: 1 new error(s) (ARCH001)'
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
- src/frob/refactor/_verify.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1885 at commit 63de87f14c7776731f11eeb926ecb88f9de43a2e found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- ARCH001  src/frob/refactor/_verify.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/refactor/_verify.py  -> attributed to T-1885 (commit 63de87f14c77, already closed/dropped -- filed below) via src/frob/refactor/_verify.py::verify_import_resolution

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.