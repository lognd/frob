---
id: T-2724
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2681):
  1 new (rule, file) identit(ies), 0 finding(s) (E501)'
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
- src/frob/_cli_parsers/_ticket/_closeout.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2681) at commit 50c9fbee7d0d81e4fced0d32fecd58026c8993b3 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 0 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- E501  src/frob/_cli_parsers/_ticket/_closeout.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E501  src/frob/_cli_parsers/_ticket/_closeout.py  -> attributed to T-2681 (commit 446a7bee8031, already closed/dropped -- filed below) via src/frob/_cli_parsers/_ticket/_closeout.py::_add_ticket_attach_and_lifecycle_end_parsers -> src/frob/_cli_parsers/_ticket/_closeout.py::_add_ticket_close_parser

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.