---
id: T-3761
title: skip win32 POSIX-only flock tests in test_process_lock.py
state: in-progress
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
- tests/unit/test_process_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: waive BUG002 confirmatory-only check for win32 platform skip
  actor: logan
  at: '2026-09-04'
  old_length: 483
  new_length: 612
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI fails TestCrossProcessPoolInheritance.test_independent_process_without_marker_still_blocks, TestDerivedStateLock.test_shared_locks_do_not_block_each_other, TestDerivedStateWriteLock.test_concurrent_separate_process_writer_still_blocked -- these depend on POSIX fcntl.flock SHARED-lock semantics and real cross-process blocking that msvcrt cannot provide identically (module docstring: 'exclusive=False (SHARED) is only meaningful on POSIX'). Add skipif(sys.platform==win32).

frob:waive BUG002 reason="win32-only skip; the POSIX-primitive dependency is not reproducible from a Linux parent-commit repro"