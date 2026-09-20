---
id: T-3782
title: fix win32 failures in scaffold warm pool tests
state: done
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
- tests/system/test_scaffold_pool.py
- src/frob/app/pool_runner.py
- src/frob/scaffold/_pool.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/app/**
  reason: narrow away from the whole app package -- massive overlap with many in-flight
    tickets
  actor: logan
  at: '2026-09-04'
- op: add
  glob: src/frob/app/pool_runner.py
  reason: the warm-pool implementation is the actual fix surface
  actor: logan
  at: '2026-09-04'
- op: add
  glob: src/frob/scaffold/_pool.py
  reason: the actual warm-pool implementation the failing tests exercise
  actor: logan
  at: '2026-09-04'
evidence:
- tests/system/test_scaffold_pool.py::TestDefaultPoolDir::test_resolves_under_git_common_dir
- tests/system/test_scaffold_pool.py::TestManifestRoundTrip::test_write_then_read_round_trips
- tests/system/test_scaffold_pool.py::TestWarmWorktree::test_creates_worktree_and_marks_ready
- tests/system/test_scaffold_pool.py::TestWarmWorktree::test_build_failure_marks_not_ready
- tests/system/test_scaffold_pool.py::TestWarmPool::test_fills_pool_to_n_slots
- tests/system/test_scaffold_pool.py::TestWarmPool::test_leaves_existing_ready_slots_alone
- tests/system/test_scaffold_pool.py::TestLeaseWorktree::test_leases_ready_slot_and_removes_it
- tests/system/test_scaffold_pool.py::TestLeaseWorktree::test_empty_pool_returns_err
- tests/system/test_scaffold_pool.py::TestLeaseWorktree::test_lease_merges_base_ref_current
- tests/system/test_scaffold_pool.py::TestRefillAsync::test_refill_thread_rewarms_slot
- tests/system/test_scaffold_pool.py::TestPoolStatus::test_status_reflects_manifest
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CI failures in tests/system/test_scaffold_pool.py::TestWarmPool (2): test_fills_pool_to_n_slots, test_leaves_existing_ready_slots_alone. Worktree pool on Windows -- likely path-separator or process-spawn shape issue.