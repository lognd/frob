---
id: T-1947
title: 'post-land sweep regression from T-1922: 2 new error(s) (DOC002, DRIFT002)'
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
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-1922 at commit b508b0ad3eecab50efe704e1d713dd01a7bd0da8 found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- DOC002  src/frob/tickets/_land.py
- DRIFT002  src/frob/tickets/_land.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC002  src/frob/tickets/_land.py  -> attributed to T-1922 (commit b508b0ad3eec, already closed/dropped -- filed below) via src/frob/tickets/_land.py::_check_committed_waive_deletions -> src/frob/tickets/_land.py::_restrict_to_branch_own_files
- DRIFT002  src/frob/tickets/_land.py  -> attributed to T-1922 (commit b508b0ad3eec, already closed/dropped -- filed below) via src/frob/tickets/_land.py::_check_committed_waive_deletions -> src/frob/tickets/_land.py::_restrict_to_branch_own_files

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-10: both findings already fixed on main: DOC002 by T-1954 (heading added to docs/modules/tickets.md), DRIFT002 x2 by T-1951 (frob:tests edges re-pointed). Verified: frob check --only doclink --only drift reports 0 errors and git grep finds no remaining stale target. Condition self-resolved via concurrent work after T-1684's sweep auto-filed this; dropping so it stops holding a high-priority starved slot.
