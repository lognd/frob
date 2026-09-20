---
id: T-3810
title: 'F-009: frob check crashes on vitest project when repo root is relative (_collect_ts
  relative_to(root) vs vitest absolute paths)'
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
- src/frob/testing/_collect_ts.py
- tests/**/*collect_ts*
- tests/test_testing.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_testing.py
  reason: test file for _collect_ts.py lives here
  actor: logan
  at: '2026-09-05'
evidence:
- tests/test_testing.py::TestCollectTsTests::test_vitest_node_id_relative_root_absolute_file
- tests/test_testing.py::TestCollectTsTests::test_ts_content_key_relative_root_absolute_file
designated_repro_test: tests/test_testing.py::TestCollectTsTests::test_vitest_node_id_relative_root_absolute_file
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
