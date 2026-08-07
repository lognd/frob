---
id: T-0799
title: 'graph cache: schema drift crashes load_graph (no such column/table) instead
  of rebuilding'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/cache.py
- src/frob/graph/__init__.py
- tests/unit/graph/test_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_symbols_table_rebuilds_clean
- tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_mtime_ns_column_rebuilds_clean
designated_repro_test: null
acceptance:
- text: GIVEN a .frob/cache.db created by an older schema WHEN load_graph opens it
    THEN it detects the schema mismatch and rebuilds the cache instead of raising
    sqlite3.OperationalError; a test opens an old-schema fixture db and asserts a
    clean rebuild
  evidence:
  - tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_symbols_table_rebuilds_clean
  - tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_mtime_ns_column_rebuilds_clean
threat: null
component: null
---
Observed twice during 2026-07-23 lands: worktrees carrying pre-migration cache.db files crashed land mid-flight with 'no such table: symbols' and 'no such column: mtime_ns' (the second crash left a partial squash staged on main). Stamp a schema version in the db and rebuild on mismatch; never let OperationalError escape load paths.