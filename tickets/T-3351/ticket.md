---
id: T-3351
title: Fix frob:tests Class::method separator in check_runner.py (2 DRIFT002 findings)
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
blocked_by:
- T-3326
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/check_runner.py
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
Deferred from T-3344 (gate:DRIFT burn-down) because T-3326 holds an in-progress lease on this file and landing would create CrossTicketLeakage. Same fix as T-3344's other 12 files: two frob:tests directives at lines ~351/354 use TestTaskProgressCallback::test_... (double-colon) instead of the graph's TestTaskProgressCallback.test_... (dot) qualname convention, so DRIFT002 flags them as unresolvable. Apply once T-3326 closes.