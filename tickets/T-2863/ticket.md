---
id: T-2863
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2840):
  2 new (rule, file) identit(ies), 21 finding(s) (F401, F822)'
state: queued
kind: bug
origin: agent
created: '2026-08-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_bug_repro.py
- src/frob/gates/_mutation_evidence.py
findings:
- - F401
  - /home/logan/projects/frob/src/frob/gates/_mutation_evidence.py
- - F822
  - /home/logan/projects/frob/src/frob/gates/_bug_repro.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2840) at commit 3c53cf5ef8dabac31f211a6608a5b2da0b339455 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 21 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- F401  /home/logan/projects/frob/src/frob/gates/_mutation_evidence.py
- F822  /home/logan/projects/frob/src/frob/gates/_bug_repro.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- F401  /home/logan/projects/frob/src/frob/gates/_mutation_evidence.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F822  /home/logan/projects/frob/src/frob/gates/_bug_repro.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.