---
id: T-1864
title: 'post-land sweep regression from T-1843: 2 new error(s) (DOCENUM001, E501)'
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
- /home/logan/projects/frob/src/frob/gates/_policy_weakening_gate.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1843 at commit cb1cc57f5589d6ffe9ace4563a249265e8e4a145 found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- DOCENUM001  docs/modules/gates.md
- E501  /home/logan/projects/frob/src/frob/gates/_policy_weakening_gate.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOCENUM001  docs/modules/gates.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/gates/_policy_weakening_gate.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.