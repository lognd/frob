---
id: T-3392
title: Resolve OPAQUE001 dynamic-key container call in test_land_finish_idempotent
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
- tests/unit/test_land_finish_idempotent.py
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
OPAQUE001: line 243 uses a runtime-resolved dynamic-key container call the capability scanner cannot statically resolve. Rework to a statically-resolvable call or declare the capability explicitly so the scanner can verify it. Part of PyPI release error-floor burn (Series EQ slice).