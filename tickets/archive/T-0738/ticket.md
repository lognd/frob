---
id: T-0738
title: 'worktree warm pool: frob scaffold pool N pre-warmed worktrees with background
  refresh'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0732
tier: ticket
sprint: null
scope:
- src/frob/scaffold/**
- Makefile
- docs/guides/**
- tests/system/test_scaffold_pool*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/system/test_scaffold_pool*.py
  reason: 'T-0738 needs test coverage under tests/ (TEST001 requires a frob:tests

    edge resolving to a real collected node id, and testpaths is restricted

    to tests/ in pyproject.toml). The original scope (src/frob/scaffold/**,

    Makefile, docs/guides/**) has no test-file glob, so tests cannot be added

    without a scope mutation. Adding a narrow glob for this ticket''s own new

    test file only.

    '
  actor: logan
  at: '2026-07-23'
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
acceptance:
- text: GIVEN a warm pool of N WHEN an agent leases a worktree THEN it starts with
    natives built and main current, and the pool refills in the background
  evidence:
  - tests/system/test_scaffold_pool.py::TestRefillAsync::test_refill_thread_rewarms_slot
threat: null
component: null
---
Part 2 of T-0732 (part 1, the shared cargo cache, landed 30.4s->11.4s): pre-create N worktrees with natives built + main merged; agents lease from the pool; a background refresh re-warms after lands. Closes the residual per-worktree crate recompile cost (cargo keys by absolute path) by amortizing it ahead of dispatch. Coordinate with T-0736's scaffold-managed blocks and T-0735's frob natives build.