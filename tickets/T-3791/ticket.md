---
id: T-3791
title: fix win32 test_cli_test frob-test-cli failures
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
- src/frob/app/*.py tests/system/test_cli_test.py
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
win32 CI: tests/system/test_cli_test.py::TestFrobTest::test_all_runs_full_suite and test_selects_bound_test_for_touched_symbol fail. Root cause TBD via winrun. Part of win32 CI drain.