---
id: T-0019
title: cache.connect does not recover from a non-sqlite-file corrupt cache.db
state: done
kind: bug
origin: human
created: '2026-07-17'
blocked_by: []
parent: null
scope:
- src/frob/graph/cache.py
evidence:
- tests/test_graph.py::TestCorruptCacheRecovery::test_garbage_cache_file_is_recreated
attachments: []
---
Discovered while writing INV-003 evidence (cache is always rebuildable): frob.graph.cache.connect() catches sqlite3.DatabaseError only around the schema-version SELECT and falls back to a fresh-rebuild path, but that path still runs DROP TABLE IF EXISTS against the same corrupt connection, which itself raises DatabaseError('file is not a database') when the on-disk bytes are not a valid sqlite file at all (as opposed to merely wrong-schema). A missing cache.db rebuilds fine (verified: tests/test_graph.py::TestLoadGraph::test_deleted_cache_is_rebuildable_from_source); a present-but-garbage cache.db does not (build_graph raises instead of returning Err or rebuilding). Fix: on DatabaseError, close and unlink/reopen the file before executescript, or catch DatabaseError around the DROP/executescript block too.

## Done report

connect() now detects a non-sqlite cache.db (probe SELECT after the
schema read fails), closes, unlinks, and recreates the file -- the cache
is derived state, so delete-and-recreate is the honest recovery. INV-003
evidence extended with the regression test.
