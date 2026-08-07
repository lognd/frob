## Done report

Fixed both defects together.

1. cache.py write/read paths outside schema application (store_file_data,
   set_root, touch_file_stat, connect_readonly) had no retry on
   "database is locked" at all -- the third instance of the T-1239/T-1416
   family the ticket asked for. Added _with_lock_retry, a shared helper
   using the same poll/backoff shape and 30s budget as the existing
   schema-application retry, and wired it into all four call sites.
   Whole-function retry is safe here because every wrapped operation is
   a delete-then-insert or a plain read, idempotent under retry.

2. On retry exhaustion, cache.py now raises CacheLocked (a narrow
   sqlite3.OperationalError subclass) instead of the bare exception.
   frob.graph.build_graph and load_graph (both already Result-returning,
   T-0976/T-0799 precedent) catch CacheLocked specifically -- distinct
   from the existing generic-OperationalError-is-CacheCorrupt branch, so
   a transient lock is never misreported as corruption -- and return
   Err(GraphError.CacheLocked) instead of letting the exception reach
   main()'s top-level handler and abort the whole check run.

Scope was widened by one file (src/frob/graph/__init__.py, via
`frob ticket scope --add` with a recorded reason) because acceptance
criterion 1 ("the failure surfaces as a typani Result the caller
handles") is only observable at the one real caller of these cache.py
functions; cache.py alone cannot demonstrate the Result contract.

Test: tests/test_graph_lock.py::TestCacheLockRetry adds the honest
reproduction the ticket asked for (test_store_file_data_retries_past_a_
held_exclusive_lock: two real sqlite connections on the same file, one
holding BEGIN IMMEDIATE while the other retries) plus unit coverage of
_with_lock_retry's retry/give-up/non-locked-passthrough behavior and
build_graph's CacheLocked -> Err(GraphError.CacheLocked) boundary.

Docs: docs/modules/graph.md gets a new "Lock contention (T-1423)"
subsection under Cache, plus the new GraphError.CacheLocked member in
the Error types code block. design/frob.strata's graphlang/testsuite
interface= attrs were refreshed via `frob sys sync-interface` for the
two new public symbols (CacheLocked, TestCacheLockRetry).

### Changed
```
 design/frob.strata         |     4 +
 docs/modules/graph.md      |    21 +
 docs/modules/serve.md      |    24 +
 frob.lock                  |     2 +-
 src/frob/graph/__init__.py |    25 +-
 src/frob/graph/cache.py    |   136 +-
 src/frob/serve/_socketd.py |    55 +
 tests/test_graph_lock.py   |   110 +-
 tests/test_serve_socket.py |   112 +
 tickets-archive.md         |  9720 +++++++++++++++++++++++++++++++++++++-
 tickets.md                 | 10745 ++++---------------------------------------
 11 files changed, 10983 insertions(+), 9971 deletions(-)
```

### Evidence
- `tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestCacheLockRetry::test_non_locked_operational_error_is_not_retried` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestCacheLockRetry::test_store_file_data_retries_past_a_held_exclusive_lock` (pytest node id, verified passing when recorded)
- `tests/test_graph_lock.py::TestCacheLockRetry::test_build_graph_reports_err_instead_of_crashing_on_cache_locked` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 7 error(s), 437 warning(s), 695 waived
- error-findings: AFFECT001@src/frob/graph/__init__.py, AFFECT002@src/frob/graph/__init__.py, COV003@tickets/T-1406, COV003@tickets/T-1408, COV003@tickets/T-1419, SELFAUDIT001@design, WIRE001@tests/test_serve_socket.py
