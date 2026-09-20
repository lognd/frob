---
id: T-4500
title: claim divergence from T-4492's Done report (2 identit(ies))
state: queued
kind: bug
origin: agent
created: '2026-09-15'
priority: high
parent: null
tier: ticket
sprint: v0.540.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/tickets/_land.py
findings:
- - COV002
  - src/frob/app/ticket_runner/_lifecycle.py
- - COV002
  - src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.540.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Deferred post-land claim-divergence check (T-2938) found that T-4492's Done report's captured gate-state claim (T-0754) no longer holds against the tree this sweep measured at ae193dce324b -- reusing this sweep's own unscoped `frob check` result as both the count and the per-finding identity source, no second spawn.

Diverging (rule, file) identit(ies):
- COV002: src/frob/app/ticket_runner/_lifecycle.py
- COV002: src/frob/tickets/_land.py

This is a report-honesty finding, not necessarily bad content on main -- the land already published; the tree itself was already covered by this land's own pre-land check plus this sweep's unscoped post-land measurement. Determine whether the claim was a stale/incorrect capture or a real self-introduced regression, fix or refresh accordingly, then dispose the quarantine entry this ticket raised.