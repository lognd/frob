---
id: T-3172
title: 'post-land sweep regression from T-3156: 2 new (rule, file) identit(ies), 7
  finding(s) (DRIFT001, SYS003)'
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
- src/frob/__init__.py
- src/frob/tickets/_evidence.py
- design/frob.strata
- frob.lock
- tickets/T-draft-5c2f8937/**
- tickets/T-draft-5853e0e6/**
findings:
- - DRIFT001
  - src/frob/tickets/_evidence.py
- - SYS003
  - src/frob/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: SYS003 fix requires declaring the Flow/node membership in the architecture
    model, not just the importing file
  actor: logan
  at: '2026-08-27'
- op: add
  glob: frob.lock
  reason: frob ack rewrites frob.lock as a side effect; frob ticket new for the two
    required follow-up tickets (docs drift, pre-existing SYS003 case) writes tickets/T-draft-*/ticket.md
    before renumbering -- both are machinery side effects of doing this ticket's own
    required work, not scope creep
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tickets/**
  reason: frob ack rewrites frob.lock as a side effect; frob ticket new for the two
    required follow-up tickets (docs drift, pre-existing SYS003 case) writes tickets/T-draft-*/ticket.md
    before renumbering -- both are machinery side effects of doing this ticket's own
    required work, not scope creep
  actor: logan
  at: '2026-08-27'
- op: remove
  glob: tickets/**
  reason: narrow the over-broad tickets/** grant to just the two draft ticket files
    this ticket's own frob ticket new calls created
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tickets/T-draft-5c2f8937/**
  reason: narrow the over-broad tickets/** grant to just the two draft ticket files
    this ticket's own frob ticket new calls created
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tickets/T-draft-5853e0e6/**
  reason: narrow the over-broad tickets/** grant to just the two draft ticket files
    this ticket's own frob ticket new calls created
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-3156 at commit 21055ca26f9b39b46b2f04c18961011be27934f5 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 7 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- DRIFT001  src/frob/tickets/_evidence.py
- SYS003  src/frob/__init__.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DRIFT001  src/frob/tickets/_evidence.py  -> attributed to T-3156 (commit 21055ca26f9b, already closed/dropped -- filed below) via src/frob/tickets/_evidence.py::_check_cmd_evidence_kind
- SYS003  src/frob/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.