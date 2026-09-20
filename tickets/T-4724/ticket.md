---
id: T-4724
title: Extract typed-id dangling-reference construction refusal for Ticket.parent
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
- src/frob/tickets/_models.py
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
- field: sprint
  old_value: v0.536.0
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
T-3032 follow-up (per-concern inventory, docs/design/ticket-strata-shared-graph-inventory.md): Ticket._validate_parent's dangling-reference refusal at construction time is a narrower, hand-written instance of the same contract strata-core's GraphSchema (T-3005) already provides generically. NOT yet extractable as a one-file change: today's strata_core.pyi only exposes reachable/worst_age/demand/vmodel_check, no generic schema-validation entry point -- needs its own design pass (does this route through the Rust extension, or a pure-Python frob.graph equivalent) before an extraction land, so this ticket is scoped to that design pass first, extraction second.