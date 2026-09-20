---
id: T-4721
title: Extract blocked_by transitive resolution into the shared graph kernel
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_doable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
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
T-3032 follow-up (per-concern inventory, docs/design/ticket-strata-shared-graph-inventory.md): frob.tickets._doable's blocked_by transitive-resolution walk (used by _open_blockers/MILE001) is the same edge-relation-closure shape as the parent/child descendants walk T-3032 already extracted (frob.graph._hierarchy), just over a different edge (blocked_by instead of parent). Extract it to a shared frob.graph home, reroute _doable.py onto it, verify existing MILE001/_open_blockers regression tests pass unchanged BEFORE landing. One concern per land, per T-3032's own method section.