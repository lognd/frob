---
id: T-3252
title: Consolidate duplicate _load_conftest test helper once T-3244's lease clears
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_conftest_stackdump.py
- tests/unit/test_conftest_suite_result_status.py
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
T-3246 added tests/unit/test_conftest_suite_result_status.py with its own _load_conftest helper (95% similar to the pre-existing one in tests/unit/test_conftest_stackdump.py, DUP001) because test_conftest_stackdump.py was under a live scope lease held by T-3244 (unrelated platform-safety burn-down) at land time and could not be edited. Once T-3244 lands/releases the lease, extract the shared loader into one helper (e.g. a small tests/unit/_conftest_test_helpers.py) and have both test files import it, removing the duplication.