---
id: T-3764
title: skip win32 os.nice tests in verify test_worker.py
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
- tests/unit/verify/test_worker.py
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
win32 CI fails TestEnsureReducedPriority.test_applies_nice_and_ionice_exactly_once and test_failed_nice_call_never_raises -- os.nice does not exist on Windows, genuinely POSIX-only. Add skipif(sys.platform==win32).