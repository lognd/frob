---
id: T-3480
title: 'post-land sweep regression from T-1691: 1 new (rule, file) identit(ies), 2
  finding(s) (DRIFT002)'
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
- src/frob/verify/_bisect.py
findings:
- - DRIFT002
  - src/frob/verify/_bisect.py
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
The deferred post-land unscoped sweep (T-1684) for T-1691 at commit ff0a01d83ce1f4423fb0ebc1d359449e4d265f7b found 3 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DRIFT002  src/frob/verify/_bisect.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC007  src/frob/verify/_bisect.py  -> attributed to T-1691 (commit ff0a01d83ce1, already closed/dropped -- filed below) via src/frob/verify/_bisect.py::BisectError
- DRIFT002  src/frob/verify/_bisect.py  -> attributed to T-1691 (commit ff0a01d83ce1, already closed/dropped -- filed below) via src/frob/verify/_bisect.py::BisectError
- SELFAUDIT001  tests/unit/verify/test_bisect.py  -> attributed to T-1691 (commit ff0a01d83ce1, already closed/dropped -- filed below) via tests/unit/verify/test_bisect.py::TestBisectUnattributedFinding

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.