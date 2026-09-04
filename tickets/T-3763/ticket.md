---
id: T-3763
title: skip win32 POSIX-only proc-cwd tests in test_land_finish_guard.py
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
- tests/unit/test_land_finish_guard.py
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
win32 CI fails TestScanForLiveWorktreeProcess.test_finds_a_process_cwd_into_the_path, TestRefuseIfWorktreeInUse.test_refuses_on_a_live_process_and_names_the_pid, TestFinishWorktree.{test_refuses_to_remove_a_worktree_a_live_process_is_cwd_into,test_force_removes_despite_a_live_process,test_finish_worktree_force_requires_reason_when_guard_would_fire} -- these depend on reading /proc/<pid>/cwd directly (both the test helper and scan_for_live_worktree_process itself), genuinely POSIX-only. Add skipif(sys.platform==win32).