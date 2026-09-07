---
id: T-4146
title: wire BARETOOL001 into gates/__init__.py's job registry
state: queued
kind: ux
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: alpha-gate
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
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
frob.gates._bare_toolchain.bare_toolchain_gate exists, is unit-tested (tests/unit/vet/test_bare_toolchain.py), but is not yet registered in _build_process_jobs (mirrors taint_gate's ProcessJob wiring one function up). Blocked on src/frob/gates/__init__.py's lease during T-3887/T-4125 (held by T-4124 at filing time) -- a one-line addition once that frees.