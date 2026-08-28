---
id: T-3160
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3152):
  1 new (rule, file) identit(ies), 1 finding(s) (missing-argument)'
state: done
kind: bug
origin: agent
created: '2026-08-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_coordinator_scripts.py
findings:
- - missing-argument
  - tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_coordinator_scripts.py::TestOrphanedForkserverCountAgreesWithReap::test_old_no_ancestor_forkserver_agrees
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3152) at commit 6d7177894395ea627f18e7229995f0da3be4e6af found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- missing-argument  tests/unit/test_coordinator_scripts.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- missing-argument  tests/unit/test_coordinator_scripts.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.