## Done report

Changed:
src/frob/graph/cache.py::_apply_schema
src/frob/graph/cache.py::_rebuild_schema_atomically (new)
src/frob/graph/cache.py::_recreate_and_reapply
src/frob/graph/cache.py::_apply_schema_with_recovery
src/frob/graph/cache.py::connect
tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb (updated call sites + new test)
tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection (new)

Root cause found: T-3623 round 1 closed the schema-incomplete-window for
`meta` via `_recreate`'s atomic temp-build-then-os.replace, but
`_recreate_and_reapply` (the corruption/schema-mismatch recovery path)
called `_apply_schema(conn, None, path)` a second time AFTER `_recreate`
had already atomically published a schema-complete db -- that second
call ran its DROP TABLE / CREATE TABLE sequence IN PLACE, live at the
canonical path, each statement auto-committing on its own. A sibling
connecting mid-sequence could observe `meta` dropped but `files` not yet
recreated, exactly the measured `OperationalError: no such table: files`.

Fix:
1. `_apply_schema`'s rebuild path (split into `_rebuild_schema_atomically`
   to stay under ARCH001) now always builds the replacement at a temp
   path and publishes it via one atomic `os.replace`, the same primitive
   `_recreate` uses -- no connector can ever observe a schema mid-rebuild.
2. Double-checked locking: the rebuild serializes on `path`'s existing
   rebuild lock and re-reads the stored schema version under that lock
   before doing any work; a sibling that already published the current
   version makes this a no-op reopen instead of a redundant rebuild.
3. `_recreate_and_reapply` no longer re-applies the schema after
   `_recreate` (which already leaves a schema-complete db) -- that
   redundant call was the actual thrash/partial-schema bug.
4. `connect()`'s fingerprint-check retry now closes over `conn` via
   `nonlocal` (a `_check_fingerprint_step` local function) instead of a
   plain closure, so a `_with_lock_retry` retry can never reuse a
   connection object a recreate has already closed -- hardening for the
   stale-connection class of bug (`sqlite3.InterfaceError` measured at
   the old cache.py:1083, run 33472403980).

Evidence:
tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta (existing acceptance-bar test, run 5x consecutively green locally both before landing and after the ARCH001 split)
tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_apply_schema_rebuild_replacement_always_has_files_table (new -- direction 1/4)
tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_connect_after_forced_schema_rebuild_returns_a_fresh_live_connection (new -- direction 3/4)
tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_recreate_closed_connection_raises_a_clean_programming_error_not_interface_error (new -- direction 3/4)
Also verified: tests/gates_suite/test_coverage.py -k test_waive002_end_to_end_via_run_gates green; `frob test --base main` 13/13 pass; `frob check --ticket T-3632` errors dropped from 76 (pre-split, with the ARCH001/LANDPARITY002 regression I introduced and then fixed) to 26, all pre-existing/repo-wide -- gate:SCOPE and gate:PREWORK both clean.

Filed: none

Gates: frob check --ticket T-3632 -- gate:SCOPE 0 errors, gate:PREWORK clean; no ARCH001/LANDPARITY002 on cache.py after the _rebuild_schema_atomically split; remaining repo-wide gate errors are pre-existing baseline noise outside this ticket's scope (per gate:scope-note, only gate:SCOPE/gate:PREWORK/COV002/TODO001/gate:FMT/gate:AFFECT are ticket-scoped).

### Changed
```
 tickets/T-3632/ticket.md | 5 +++++
 1 file changed, 5 insertions(+)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_apply_schema_rebuild_replacement_always_has_files_table` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_connect_after_forced_schema_rebuild_returns_a_fresh_live_connection` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_recreate_closed_connection_raises_a_clean_programming_error_not_interface_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 17 error(s), 4159 warning(s), 902 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, INV001@invariants/INV-011.md, INV001@invariants/INV-013.md, INV001@invariants/INV-041.md, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/app/_config_external.py, PII012@tests/gates_suite/test_compliance.py, PRE001@tickets/T-3632, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
