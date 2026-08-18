---
id: T-2477
title: 'post-land sweep regression from T-1135: 5 new (rule, file) identit(ies), 0
  finding(s) (E501, F401)'
state: queued
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
- src/frob/gates/__init__.py
- src/frob/gates/_dup_graph_schema.py
- src/frob/verify/_worker.py
- src/frob/vet/_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-1135 at commit bbdcc97bd8c3f2ad469ade1dd179a5959bec4db8 found 5 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (5), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 0 actual finding(s) across those 5 identit(ies).

New (rule, file) identit(ies) filed here:

- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_query.py
- E501  /home/logan/projects/frob/src/frob/gates/__init__.py
- E501  /home/logan/projects/frob/src/frob/gates/_dup_graph_schema.py
- E501  /home/logan/projects/frob/src/frob/verify/_worker.py
- F401  /home/logan/projects/frob/src/frob/vet/_capability.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_query.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/gates/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/gates/_dup_graph_schema.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/verify/_worker.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F401  /home/logan/projects/frob/src/frob/vet/_capability.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.