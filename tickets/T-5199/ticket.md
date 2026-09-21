---
id: T-5199
title: 'ticket_runner _close_cmd/_lifecycle: batch repeated load_queue calls (M4/M5)'
state: queued
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_lifecycle.py
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
found while working T-5135 perf audit (M4/M5, lower priority, not fixed there to stay in the H2-H5/M7 fix order the ticket specified): frob ticket work --cluster and frob ticket close each call load_queue multiple times (four loads measured) instead of loading once and threading the queue through. Batch to one load_queue per command invocation.