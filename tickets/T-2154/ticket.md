---
id: T-2154
title: 'post-land sweep regression from T-2125: 2 new (rule, file) identit(ies), 5
  finding(s) (E402, E501)'
state: queued
kind: bug
origin: agent
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- /home/logan/projects/frob/src/frob/tickets/_unlanded.py
- /home/logan/projects/frob/tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2125 at commit 5da87ec3f37553aac0c9b552e64efdcfa2805650 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 5 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- E402  /home/logan/projects/frob/tests/test_ticket_leases.py
- E501  /home/logan/projects/frob/src/frob/tickets/_unlanded.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E402  /home/logan/projects/frob/tests/test_ticket_leases.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/tickets/_unlanded.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.