---
id: T-5084
title: land-status.json keeps phase=running entries for dead pids (T-4562 and T-4230
  today, 2-4 hours old) and LandInProgress then refuses ledger writes from ROOT while
  no land runs; prune entries whose pid is gone on every read and treat only live
  pids as in progress
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
