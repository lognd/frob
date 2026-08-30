---
id: T-3490
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3481):
  5 new (rule, file) identit(ies), 12 finding(s) (WIRE002)'
state: queued
kind: bug
origin: agent
created: '2026-08-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/gates/_arch.py
- src/frob/gates/_coverage_sites.py
- src/frob/gates/_render_lint.py
- tests/unit/test_new_ticket_scope_overlap_warning.py
findings:
- - WIRE002
  - src/frob/app/ticket_runner/_land_cmd.py
- - WIRE002
  - src/frob/gates/_arch.py
- - WIRE002
  - src/frob/gates/_coverage_sites.py
- - WIRE002
  - src/frob/gates/_render_lint.py
- - WIRE002
  - tests/unit/test_new_ticket_scope_overlap_warning.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3481) at commit f21e301c722ba015d94db1d3020dcdb028515274 found 5 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (5), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 12 actual finding(s) across those 5 identit(ies).

New (rule, file) identit(ies) filed here:

- WIRE002  src/frob/app/ticket_runner/_land_cmd.py
- WIRE002  src/frob/gates/_arch.py
- WIRE002  src/frob/gates/_coverage_sites.py
- WIRE002  src/frob/gates/_render_lint.py
- WIRE002  tests/unit/test_new_ticket_scope_overlap_warning.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- WIRE002  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE002  src/frob/gates/_arch.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE002  src/frob/gates/_coverage_sites.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE002  src/frob/gates/_render_lint.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE002  tests/unit/test_new_ticket_scope_overlap_warning.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.