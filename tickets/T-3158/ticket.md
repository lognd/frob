---
id: T-3158
title: 'post-land sweep regression from T-3139: 2 new (rule, file) identit(ies), 1
  finding(s) (DOC006, DRIFT001)'
state: in-progress
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
- scripts/fleet_status.py
- tickets/T-3155/ticket.md
findings:
- - DOC006
  - tickets/T-3155/ticket.md
- - DRIFT001
  - scripts/fleet_status.py
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
The deferred post-land unscoped sweep (T-1684) for T-3139 at commit 6f04de4c8990f9e7e1131b420ba5c722cb95fb84 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  tickets/T-3155/ticket.md
- DRIFT001  scripts/fleet_status.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  tickets/T-3155/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  scripts/fleet_status.py  -> attributed to T-3139 (commit 6f04de4c8990, already closed/dropped -- filed below) via scripts/fleet_status.py::_ORPHAN_AGE_FLOOR_S

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.