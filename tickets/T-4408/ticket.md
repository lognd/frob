---
id: T-4408
title: Windows platform_skipped path-separator mismatch
state: done
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect.py
- tests/test_testing_collect.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_testing_collect.py
  reason: add test coverage for windows path parsing fix
  actor: logan
  at: '2026-09-10'
evidence:
- tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_windows_backslash_path_normalizes_to_posix
- tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_windows_crlf_and_nested_backslash_path
- tests/test_testing_collect.py::TestParsePlatformSkippedWindowsPathShape::test_posix_path_is_unaffected
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
probe