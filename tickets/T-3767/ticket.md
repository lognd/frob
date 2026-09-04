---
id: T-3767
title: skip win32-only fcntl/proc land-lock and worktree tests
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
- tests/test_ticket_leases.py
- tests/test_worktree_guard.py
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
Win32 CI failures depending on fcntl.flock/SIGKILL kernel-release semantics or /proc-based live-process cwd detection, unavailable on win32. Skip: TestRefuseIfLandInProgress.test_allows_after_a_killed_lands_lock_is_os_released, TestRemoveWorktree.test_keeps_a_live_process_worktree (test_ticket_leases.py); TestSweepWorktreesLiveProcess.test_clean_no_lease_recent_head_live_process_kept and test_force_overrides_the_live_process_keep (test_worktree_guard.py, reads /proc/pid/cwd directly). NOTE: TestDispatchLandGuard.test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_dispatches does not touch fcntl/proc -- left as needs win triage, not skipped. TestAgentEnvStdoutPurity.test_bare_eval_succeeds_with_no_filtering shells to bash -c eval, not clearly POSIX-only -- also left as needs win triage.