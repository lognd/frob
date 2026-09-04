---
id: T-3786
title: fix win32 path-separator bug in frob cycle graph node ids
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
- src/frob/app/cycle_runner.py
- tests/unit/test_cycle_runner_root_resolution.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_cycle_runner_root_resolution.py
  reason: add the test file this fix's evidence lives in
  actor: logan
  at: '2026-09-04'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI: 5 tests in tests/unit/test_cycle_runner_root_resolution.py fail because _process_path builds graph node ids with bare str(rel_path) (backslash-separated on win32) while tests (and downstream consumers) expect POSIX-separated ids like 'src/pkg/a.py'. Same root-cause pattern as T-3784's DEPR005 fix. Part of win32 CI drain.