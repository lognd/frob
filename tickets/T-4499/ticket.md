---
id: T-4499
title: 'post-land sweep regression from T-4491: 2 new (rule, file) identit(ies) (COV002)'
state: queued
kind: bug
origin: agent
created: '2026-09-15'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design/frob.strata
- src/frob/tickets/_leases.py
findings:
- - COV002
  - design/frob.strata
- - COV002
  - src/frob/tickets/_leases.py
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
The deferred post-land unscoped sweep (T-1684) for T-4491 at commit 5a1bb2984ceaa704237c8a6f567dd9fb138b5f56 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- COV002  design/frob.strata
- COV002  src/frob/tickets/_leases.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV002  design/frob.strata  -> attributed to T-4491 (commit 5a1bb2984cea, already closed/dropped -- filed below) via design/frob.strata::frob.testsuite
- COV002  src/frob/tickets/_leases.py  -> attributed to T-4491 (commit 5a1bb2984cea, already closed/dropped -- filed below) via src/frob/tickets/_leases.py::_active_ledger_cache_signature

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.