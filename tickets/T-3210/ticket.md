---
id: T-3210
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2728):
  2 new (rule, file) identit(ies), 0 finding(s) (FLAGCOV001, TICK002)'
state: queued
kind: bug
origin: agent
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- frob.toml
- tickets.md
findings:
- - FLAGCOV001
  - frob.toml
- - TICK002
  - tickets.md
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2728) at commit 61709cf9ff5f5464a1d61cb0eef24cff19a1a9d9 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 0 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- FLAGCOV001  frob.toml
- TICK002  tickets.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- FLAGCOV001  frob.toml  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK002  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.