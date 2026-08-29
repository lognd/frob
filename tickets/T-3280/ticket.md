---
id: T-3280
title: 'post-land sweep regression from T-3251: 2 new (rule, file) identit(ies), 2
  finding(s) (COV007, DOC006)'
state: queued
kind: bug
origin: agent
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/verify_release_ci_status.py
- tickets/T-3272/ticket.md
findings:
- - COV007
  - scripts/verify_release_ci_status.py
- - DOC006
  - tickets/T-3272/ticket.md
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
The deferred post-land unscoped sweep (T-1684) for T-3251 at commit 159251143da3feaf975d87513b2b80da446c226f found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- COV007  scripts/verify_release_ci_status.py
- DOC006  tickets/T-3272/ticket.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV007  scripts/verify_release_ci_status.py  -> attributed to T-3251 (commit 159251143da3, already closed/dropped -- filed below) via scripts/verify_release_ci_status.py::CiStatusResult
- DOC006  tickets/T-3272/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Failure log
- 2026-08-29 attempt 1: already resolved on main: neither finding reproduces -- frob check --only docblocks shows 0 DOC006 findings against tickets/T-3272/ticket.md, and frob check --only coverage shows 0 COV007 findings against scripts/verify_release_ci_status.py (the file exists; only pre-existing waived COV007 identities remain elsewhere). T-3251 (the attributed source of the COV007 finding) is already closed/dropped per this ticket's own attribution note
