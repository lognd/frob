---
id: T-2022
title: 'post-land sweep regression from T-2004: 3 new (rule, file) identit(ies) (COV003,
  F401)'
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- /home/logan/projects/frob/tests/test_gates_fmt_directives.py
- /home/logan/projects/frob/tests/unit/test_tickets_evidence_only_scope.py
- tickets/T-0907
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2004 at commit 8a56691e75595b2914b52de4b8894452bd30add9 found 3 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- COV003  tickets/T-0907
- F401  /home/logan/projects/frob/tests/test_gates_fmt_directives.py
- F401  /home/logan/projects/frob/tests/unit/test_tickets_evidence_only_scope.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV003  tickets/T-0907  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F401  /home/logan/projects/frob/tests/test_gates_fmt_directives.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F401  /home/logan/projects/frob/tests/unit/test_tickets_evidence_only_scope.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.