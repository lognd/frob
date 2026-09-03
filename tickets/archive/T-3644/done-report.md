## Done report

Retired WAL journal mode on the graph cache (PRAGMA journal_mode=TRUNCATE) to
structurally eliminate the -shm mmap SIGBUS class that survived four prior
atomicity-hardening rounds (T-3607/T-3623/T-3632/T-3634). Kept all their
atomic-rebuild machinery.

TRUNCATE moves locking onto sqlite's rollback-journal fcntl advisory locks,
which do not correctly exclude two sqlite3.Connection objects opened by the
SAME process against the SAME file (documented SQLite/POSIX caveat) -- this
surfaced as the same T-1423 transient-lock contention now showing up as
"attempt to write a readonly database" instead of "database is locked", so
widened _with_lock_retry's match to catch both shapes. That alone was not
enough under the two-thread same-process test (test_two_processes_never_
commit_to_the_same_cache_concurrently, ~20-40% flaky) -- added a per-
resolved-path in-process threading.RLock (_inprocess_write_lock), held only
for connect()'s own call (not the returned connection's whole lifetime,
which was tried first and deadlocked T-0232's pinned
test_connect_on_current_schema_does_not_block_on_a_held_write_lock
invariant).

Evidence: test_two_processes_never_commit_to_the_same_cache_concurrently
10/10 clean; test_connect_after_forced_schema_rebuild_returns_a_fresh_live_
connection and test_recreate_closed_connection_raises_a_clean_programming_
error_not_interface_error clean; test_connect_on_current_schema_does_not_
block_on_a_held_write_lock clean (T-0232 invariant preserved). Combined
test_graph_cache.py + test_graph_build_lock.py + test_graph_lock.py +
test_graph.py: 181/181 across 4 consecutive full runs. BUG002-waived: the
production defect is a SIGBUS (fatal OS signal), not reproducible as a
deterministic local test failure -- see the frob:waive BUG002 body entry
for the full reasoning.

Noted, not fixed (pre-existing, out of this ticket's root cause):
test_two_processes_connecting_concurrently_never_see_no_such_table_meta has
a measured pre-existing flake under baseline WAL (1/8) and a comparable
flake rate under this patch, from real CPU/disk contention in a tight
no-sleep rebuild loop, present under both journal modes.

Gates: ruff-check and ty clean on cache.py; ruff-format clean except one
pre-existing unrelated line-join nit, untouched by this diff, left as out
of scope. Filed: none new -- T-3643 (TICKET A) was already filed earlier
this series.

### Changed
```
 src/frob/graph/cache.py       | 159 ++++++++++++++++++++++++++++++++++--------
 tickets/T-3644/done-report.md |  59 ++++++++++++++++
 2 files changed, 190 insertions(+), 28 deletions(-)
```

### Evidence
- `tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope::test_two_processes_never_commit_to_the_same_cache_concurrently` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_connect_after_forced_schema_rebuild_returns_a_fresh_live_connection` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_recreate_closed_connection_raises_a_clean_programming_error_not_interface_error` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestConcurrentCache::test_connect_on_current_schema_does_not_block_on_a_held_write_lock` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 16 error(s), 4279 warning(s), 897 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT002@src/frob/vet/_capability_core.py, DRIFT002@src/frob/vet/_capability_python.py, DRIFT002@src/frob/vet/_capability_scan.py, DRIFT002@src/frob/vet/_supplychain.py, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
