---
id: T-4409
title: _collect.py exceeds LARGE001 800-line threshold
state: queued
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: null
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: 0.531.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect.py
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
LARGE001: src/frob/testing/_collect.py is 895 lines, over the 800-line threshold, and will red the next ubuntu self-gate. Filed for tracking only per coordinator brief -- another agent owns this file and the COV/TEST gate attribution around it; do NOT dispatch a fix here without coordinating, extract a cohesive private module the same way T-4407 split verify_runner.py.