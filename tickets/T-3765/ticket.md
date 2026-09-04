---
id: T-3765
title: skip win32 /proc starttime tests in test_mutate_journal.py
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
- tests/test_mutate_journal.py
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
win32 CI fails test_recycled_pid_with_mismatched_starttime_is_treated_stale and test_pytest_session_start_restores_leftover_journal -- both depend on /proc/<pid>/stat starttime (module docstring: 'This is Linux-specific (/proc is not portable)'), genuinely POSIX-only. Add skipif(sys.platform==win32).