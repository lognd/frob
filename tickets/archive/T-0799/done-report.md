## Done report

Fixed load_graph() (src/frob/graph/__init__.py) to catch sqlite3.OperationalError
across its entire read body, not just the get_root() query. The writer path
(cache.connect()) already stamped/checked a schema version (meta.schema_version,
_SCHEMA_VERSION=3) and self-healed via DROP+recreate on mismatch or any
DatabaseError during DDL -- that mechanism was already correct and untouched.

The actual bug was in the READ-ONLY path: connect_readonly() opens a cache.db
with no schema-version check at all (a read-only connection cannot self-heal),
so a pre-migration cache.db (missing the 'symbols' table, or missing the
'mtime_ns' column T-0245 added) crashed with a raw sqlite3.OperationalError
the moment any query after get_root() touched the drifted shape --
_first_stale_cached_file, _first_added_file, or load_all. Only get_root()
itself was guarded by a try/except; everything after it in the same try block
had no except clause at all (only a finally), so the OperationalError
propagated straight out of load_graph and crashed callers mid-land.

Fix: wrapped the whole read body (get_root through load_all) in one try, with
an explicit sqlite3.OperationalError handler (schema drift -> CacheCorrupt)
ahead of the existing sqlite3.DatabaseError handler (corrupt bytes ->
CacheCorrupt). No versioning scheme changes: this repo already has one
(meta.schema_version) that the writer honors; the read path just needed to
stop letting its query errors escape uncaught. Every real load_graph() caller
already falls back to build_graph() on Err, so CacheCorrupt now triggers a
clean rebuild instead of a crash.

Regression tests (tests/unit/graph/test_cache.py, new file, in ticket scope):
hand-crafted two fixture cache.db files -- (a) missing the symbols table
entirely, (b) missing the mtime_ns/size columns on files (pre-T-0245 shape) --
and assert load_graph() returns Err(CacheCorrupt) rather than raising, then
assert build_graph() against the same path rebuilds cleanly and a subsequent
load_graph() succeeds.

Verified: uv run --frozen pytest tests/unit/graph/ -q -> 37 passed.
uv run --frozen frob check --ticket T-0799 --only prework/lint/static/gates-fast
all pass (0 errors each stage).

Deviations: none from the ticket's plan. cache.py itself needed no change --
its schema-version stamping already existed (T-0279/T-0245); the gap was
entirely in __init__.py's load_graph read-error handling.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_symbols_table_rebuilds_clean` (pytest node id, verified passing when recorded)
- `tests/unit/graph/test_cache.py::TestSchemaDriftRebuild::test_missing_mtime_ns_column_rebuilds_clean` (pytest node id, verified passing when recorded)
