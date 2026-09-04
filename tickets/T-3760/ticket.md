---
id: T-3760
title: skip win32 POSIX-only /proc tests in test_process_reap.py
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
- tests/unit/test_process_reap.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_terminates_old_orphaned_forkservers
- tests/unit/test_process_reap.py::TestReapOrphanedForkservers::test_forkserver_of_orphaned_forkserver_is_reaped
- tests/unit/test_process_reap.py::TestCountRunningChecks::test_counts_other_check_processes
- tests/unit/test_process_reap.py::TestCountRunningChecks::test_excludes_self
- tests/unit/test_process_reap.py::TestCountRunningChecks::test_ignores_non_check_processes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI fails these tests because they exercise /proc scanning directly (forkserver reap age/ppid checks, count_running_checks argv scan) -- genuinely POSIX-only, add skipif(sys.platform==win32).