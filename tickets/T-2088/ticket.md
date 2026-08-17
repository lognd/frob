---
id: T-2088
title: 'post-land sweep regression from T-2086: 1 new (rule, file) identit(ies), 4
  finding(s) (PII012)'
state: dropped
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/testing/_coverage_refresh.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2086 at commit 96797165abbda2bdf96be3e2b12d13a0b2e30a25 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 4 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- PII012  src/frob/testing/_coverage_refresh.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- PII012  src/frob/testing/_coverage_refresh.py  -> attributed to T-2086 (commit f843ad7ed5ff, already closed/dropped -- filed below) via src/frob/testing/_coverage_refresh.py::_XDIST_DIST_FLAGS

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-10: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (PII012 src/frob/testing/_coverage_refresh.py) is absent from the fresh unscoped measurement at T-2069's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
