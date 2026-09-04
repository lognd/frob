---
id: T-3760
title: skip win32 POSIX-only /proc tests in test_process_reap.py
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
- tests/unit/test_process_reap.py
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
win32 CI fails these tests because they exercise /proc scanning directly (forkserver reap age/ppid checks, count_running_checks argv scan) -- genuinely POSIX-only, add skipif(sys.platform==win32).