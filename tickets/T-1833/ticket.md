---
id: T-1833
title: 'post-land sweep regression from T-1821: 1 new error(s) (unresolved-import)'
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
- tests/unit/strata/test_capacity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1821 at commit 5518834deef19d2676526b897f8415b8b7350c4c found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- unresolved-import  tests/unit/strata/test_capacity.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- unresolved-import  tests/unit/strata/test_capacity.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-08: Verified in a warm worktree (natives built): uv run ty check tests/unit/strata/test_capacity.py passes clean, and every frob.strata import the file uses resolves in this worktree venv. This is the same environment-artifact class as today's test_capacity.py investigation -- the T-1821 detached sweep ran in a cold worktree missing built strata_core/frob_core natives, producing a false unresolved-import. No code change.
