---
id: T-1214
title: 'perf: graph/cache load_file_data issues 3 sqlite queries per file -- batch
  whole-table SELECTs'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/graph/cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/graph.md
  reason: AFFECT001 requires a one-line note on load_all's doc anchor for the T-1214
    batching change
  actor: logan
  at: '2026-08-03'
- op: remove
  glob: docs/modules/graph.md
  reason: 'reverting: adding this shared doc file to scope pulls in scope-closure
    obligations for the whole graph module''s other public symbols; waiving AFFECT001
    at the call site instead, since load_all''s documented behavior is unchanged'
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_graph.py::TestCacheModule::test_store_and_load_file_data_roundtrip
- tests/test_graph.py::TestCacheModule::test_set_root_and_get_root_roundtrip
- tests/test_graph.py::TestCacheModule::test_tests_edge_direction_agrees_fresh_parse_vs_cache_roundtrip
designated_repro_test: null
acceptance:
- text: 'GIVEN load_file_data (graph/cache.py:560) issues 3 sqlite execute calls per
    file (5595 execute calls per load_all across ~1865 files) plus json.loads on every
    attrs value including the common attrs==''{}'' case WHEN load_all does 3 whole-table
    SELECTs ordered by path and groups rows in Python (or batches an executemany-style
    IN query per chunk), and skips json.loads for attrs==''{}'' THEN snapshot loading
    drops ~1s native off every gate/CLI invocation that loads it (report candidate
    #8)'
  evidence:
  - tests/test_graph.py::TestCacheModule::test_store_and_load_file_data_roundtrip
  - tests/test_graph.py::TestCacheModule::test_set_root_and_get_root_roundtrip
  - tests/test_graph.py::TestCacheModule::test_tests_edge_direction_agrees_fresh_parse_vs_cache_roundtrip
threat: null
component: null
---
Root cause: graph/cache.py:564-587 load_file_data does 3 queries per file instead of 3 queries total. Fix: in load_all, replace the per-file query loop with 3 whole-table SELECTs (or chunked IN-batched queries) ordered by path, group rows in Python; add a fast path skipping json.loads when attrs == '{}'.