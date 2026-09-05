---
id: T-3797
title: guarded_subprocess_run must not raise on a missing/unlaunchable executable
  (win32 [WinError 2] crashed frob doctor)
state: done
kind: bug
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
- src/frob/process/_guard.py
- tests/unit/test_process_guard.py
- tickets/T-3802/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-3802/ticket.md
  reason: filing this follow-up ticket in-worktree auto-committed its ticket.md into
    T-3797's diff
  actor: logan
  at: '2026-09-05'
evidence:
- tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_missing_binary_returns_err_spawn_failed_never_raises
designated_repro_test: tests/unit/test_process_guard.py::TestGuardedSubprocessRun::test_missing_binary_returns_err_spawn_failed_never_raises
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
