---
id: T-4047
title: 'T-4018 follow-up: _read_root still guards fetchone() with is-not-None'
state: done
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
- tests/unit/test_graph_cache.py
scope_breadth_ack: true
scope_breadth_ack_reason: cache.py's shared meta-table helpers (get_root, get_file_meta,
  etc.) carry frob:doc/frob:tests reverse-edges fanning across the whole graph subsystem
  doc (docs/modules/graph.md) and test_graph.py -- same T-3914/T-4018 scope-closure-breadth
  pattern; out of proportion to pull in for a one-symbol guard fix
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_graph_cache.py
  reason: add fixture covering _read_root's fetchone() truthiness guard, mirroring
    T-4018's fixture pattern
  actor: logan
  at: '2026-09-06'
evidence:
- tests/unit/test_graph_cache.py::TestReadRootEmptyRowGuard::test_empty_root_row_is_a_clean_miss_not_a_crash
- tests/unit/test_graph_cache.py::TestReadRootEmptyRowGuard::test_genuine_root_still_returns_unchanged
- tests/unit/test_graph_cache.py::TestReadRootEmptyRowGuard::test_empty_root_row_logs_a_warning_naming_table_and_key
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4018 fixed 7 fetchone()-guard sites in cache.py/_cache.py but missed
_read_root (originally reported as the line-1679 site) -- it was mistakenly
conflated with _get_file_hash during the fix. _read_root still does
row[0] if row is not None else None, so an empty-tuple fetchone() result
still raises IndexError there. Fix: truthiness guard (if row) plus the
same _warn_if_empty_row(table="meta", key="root") call used at the sibling
meta-table sites (_read_schema_version, _check_fingerprint).