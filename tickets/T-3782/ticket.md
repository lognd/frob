---
id: T-3782
title: fix win32 failures in scaffold warm pool tests
state: queued
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/**
- tests/system/test_scaffold_pool.py
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
Windows CI failures in tests/system/test_scaffold_pool.py::TestWarmPool (2): test_fills_pool_to_n_slots, test_leaves_existing_ready_slots_alone. Worktree pool on Windows -- likely path-separator or process-spawn shape issue.