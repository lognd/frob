---
id: T-2052
title: 'post-land sweep regression from T-2046: 1 new (rule, file) identit(ies), 1
  finding(s) (PERF004)'
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
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2046 at commit 0e47e024fc1e6c6947fddf7536a9ad592e3832d1 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- PERF004  src/frob/tickets/_land.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- PERF004  src/frob/tickets/_land.py  -> attributed to T-2046 (commit 38074dd92c2c, already closed/dropped -- filed below) via src/frob/tickets/_land.py::_commit_orphaned_new_ticket_dir_only_drift -> src/frob/tickets/_land.py::_ORPHANED_NEW_TICKET_DIR_RE

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.