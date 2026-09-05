---
id: T-3921
title: add a jest test collector (frob.testing._collect_ts currently vitest-only)
state: queued
kind: feature
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_ts.py
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
Found while working T-3847 (evidence verification bucket wiring). frob.testing.collect_ts_tests only recognizes vitest (_package_json_uses_vitest gates it); jest is a distinct JS/TS test runner with its own CLI invocation, JSON reporter shape, and test-id spelling -- collecting it is genuine new collector work, not a generalization of the existing vitest path, so it is out of T-3847's bug-fix scope. Decide jest's node-id shape (jest --listTests / --json reporter) and either extend _collect_ts.py to dispatch on which runner a package.json declares, or add a sibling collect_jest_tests + LANGUAGE_COLLECTORS entry (frob.testing._collect.LANGUAGE_COLLECTORS, T-3847).