---
id: T-0141
title: 'cache corrupt-recovery crashes on Python 3.12 sqlite: DROP TABLE raises before
  rebuild'
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/cache.py
- tests/test_graph.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated
- tests/test_graph.py::TestCorruptCacheRecovery::test_truncated_sqlite_header_is_recreated
- tests/test_graph.py::TestCorruptCacheRecovery::test_ddl_failure_after_connect_probe_passes_is_recovered
designated_repro_test: null
threat: null
component: null
---
CI (python 3.12) fails tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated: cache.connect detects the unreadable db (logs 'rebuilding') but _apply_schema then runs DROP TABLE IF EXISTS on the same corrupt connection and 3.12's sqlite raises sqlite3.DatabaseError('file is not a database') -- the T-0019 delete-and-rebuild contract never engages. Local 3.11 passes, so the recovery path is version-sensitive. Fix: when the db is detected unreadable (or when any DatabaseError escapes schema application), CLOSE the connection, DELETE the file, and reconnect fresh instead of issuing DDL over the corrupt handle; must pass on 3.11 AND 3.12 (parametrize CI already covers both).