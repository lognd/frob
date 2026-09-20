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
scope:
- tests/ticket_land_suite/test_land_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/ticket_land_suite/test_land_lock.py
  reason: 'T-5084: TestLandStatus already covers _write_land_status/_read_land_status_entries
    in this file; the new dead-pid-pruned-on-read test belongs alongside it'
  actor: logan
  at: '2026-09-20'
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
