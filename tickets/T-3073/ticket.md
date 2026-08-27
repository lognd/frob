---
id: T-3073
title: Replace runtime make core spawns with frob natives build
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/scaffold/_pool.py
- tests/system/test_scaffold_pool.py
- tests/unit/test_land_cmd.py
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
Measured for T-1382. Two runtime call sites spawn make core directly instead of frob natives build: _land_cmd.py:2996 and _pool.py:206. Fails on machines without make.