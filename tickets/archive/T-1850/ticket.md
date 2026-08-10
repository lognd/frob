---
id: T-1850
title: 'post-land sweep regression from T-1545: 2 new error(s) (invalid-argument-type,
  invalid-type-form)'
state: dropped
kind: bug
origin: agent
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/strata/_sync_may.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1545 at commit 55c397088eb3fb1b275cd7575aabb3098c0e8021 found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- invalid-argument-type  src/frob/strata/_sync_may.py
- invalid-type-form  src/frob/strata/_sync_may.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- invalid-argument-type  src/frob/strata/_sync_may.py  -> attributed to T-1545 (commit 55c397088eb3, already closed/dropped -- filed below) via src/frob/strata/_sync_may.py::FileMayExtendedSyncResult
- invalid-type-form  src/frob/strata/_sync_may.py  -> attributed to T-1545 (commit 55c397088eb3, already closed/dropped -- filed below) via src/frob/strata/_sync_may.py::FileMayExtendedSyncResult

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-08: Does not reproduce: commit 87298c57f9e354e2af84a45b171b9535ab1da2b5 (T-1857, landed before this drop) already fixed 'invalid-type-form'/'invalid-argument-type' ty errors in src/frob/strata/_sync_may.py. 'uv run frob check --ticket T-1850 --json' on the current merged tree contains zero diagnostics with either code anywhere in the run.
