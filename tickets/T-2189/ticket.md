---
id: T-2189
title: 'frob ticket land --plan --dry-run is not a dry run: it created a real merge
  commit on main, then reported PlanTickGateDirty and claimed an unwind that never
  happened, stranding a draft id'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
