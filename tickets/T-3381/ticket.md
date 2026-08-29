---
id: T-3381
title: Refresh follow_up on two closed-ticket WIRE001 waivers (WIRE002)
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
- src/frob/gates/_tdd_order.py
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
WIRE002 flags conftest.py::pytest_internalerror and _tdd_order.py's tdd_order_violations frob:waive WIRE001 lines: their follow_up cites T-3246 and T-3009/T-3057, both now closed, so WIRE002 requires a live open ticket. Both waivers are permanent (genuinely-wired, not deferred work) -- this ticket exists only to hold the follow_up pointer WIRE002 requires; revisit only if either wiring claim needs re-verifying.