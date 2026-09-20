---
id: T-4720
title: Extract blocked_by/parent mutation cycle refusal into the shared graph kernel
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
- src/frob/tickets/_setters.py
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
T-3032 follow-up (per-concern inventory, docs/design/ticket-strata-shared-graph-inventory.md): frob.tickets._setters's cycle refusal on a frob ticket block/reparent mutation is the single most reusable graph primitive the T-3032 owner directive names ('LIKELY SHARED'). strata's own DAG-shaped declarations need identical cycle refusal. Best done after the blocked_by transitive-resolution extraction (a separate follow-up ticket) since cycle detection over blocked_by naturally builds on that edge relation's closure walk. Prove existing block/reparent regression tests cover current cycle-refusal behaviour before extracting; one concern per land.