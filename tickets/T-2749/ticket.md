---
id: T-2749
title: 'post-land sweep regression from T-2738: 2 new (rule, file) identit(ies), 7
  finding(s) (ARCH103, DRIFT002)'
state: queued
kind: bug
origin: agent
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/tickets/_land.py
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
The deferred post-land unscoped sweep (T-1684) for T-2738 at commit b864a1074d3e74064cd98a0e3322b27064cedbf9 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 7 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH103  src/frob/app/ticket_runner/_close_cmd.py
- DRIFT002  src/frob/tickets/_land.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  src/frob/app/ticket_runner/_close_cmd.py  -> attributed to T-2738 (commit b864a1074d3e, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_close_cmd.py::_close -> src/frob/app/ticket_runner/_close_cmd.py::_close_failure_hint -> src/frob/app/ticket_runner/_close_cmd.py::_hint_invalid_transition
- DRIFT002  src/frob/tickets/_land.py  -> attributed to T-2738 (commit b864a1074d3e, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_close_cmd.py::_close -> src/frob/app/ticket_runner/_close_cmd.py::_close_guards_for_ticket -> src/frob/app/ticket_runner/_close_cmd.py::_close_mutation_evidence_for_ticket -> src/frob/tickets/_land.py::_must_still_pass_land_violations -> src/frob/tickets/_land.py::_must_still_pass_waiver_reason -> src/frob/tickets/_land.py::_BUG003_WAIVER_RE

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.