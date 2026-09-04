---
id: T-3789
title: fix win32 test_scaffold_pool lease/status/refill failures
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
- src/frob/scaffold/*.py tests/system/test_scaffold_pool.py
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
win32 CI: 4 tests fail in tests/system/test_scaffold_pool.py (TestLeaseWorktree.test_lease_merges_base_ref_current, TestLeaseWorktree.test_leases_ready_slot_and_removes_it, TestPoolStatus.test_status_reflects_manifest, TestRefillAsync.test_refill_thread_rewarms_slot). Root cause TBD via winrun. Part of win32 CI drain.

## Failure log
- 2026-09-04 attempt 1: all 4 named tests in tests/system/test_scaffold_pool.py (TestLeaseWorktree, TestPoolStatus, TestRefillAsync) already pass on win32 (winrun-confirmed); no fix needed
