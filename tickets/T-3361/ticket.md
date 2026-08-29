---
id: T-3361
title: fix stale mock signature in test_ticket_close_bug002_t1427
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
- tests/unit/test_ticket_close_bug002_t1427.py
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
T-3104 added a keyword-only env_absent param to frob.gates._bug_repro._bug_repro_outcome_at_ref. TestCloseRefusesBug002ShapeEndToEnd's two monkeypatch lambdas still have the OLD 3-positional-arg signature (root, test_id, base_ref), so the real call site (which now passes env_absent=...) raises TypeError: got an unexpected keyword argument 'env_absent'. Test-only drift, not a product defect -- widen the lambda signatures to accept the new kwarg.