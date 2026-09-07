---
id: T-4243
title: Fix three Windows land/lease test failures
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: critical
parent: T-4236
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_leases.py
- tests/ticket_land_suite/test_wip.py
- tests/ticket_land_suite/test_land_lock.py
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_land.py
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
Three Windows-only failures under T-4236 remainder class. 1) reclaim test asserts clean tree, finds land.lock untracked. 2) normalization-only-dirty test asserts dirty, finds clean. 3) reclaim-and-logged test expects a log line, gets none.