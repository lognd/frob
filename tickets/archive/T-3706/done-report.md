## Done report

Darwin escape shape (run 33680767948): the sibling connect loop crashed
silently mid-run -- dozens of "fingerprint None -> ... invalidating cached
rows" lines and NO OK:/ERRORS: result line, because the child process's own
uncaught exception traceback went to stderr, which the test does not
capture. Confirmed the underlying cause directly (not assumed): sqlite
raises the "file is not a database" torn-read shape as a bare
sqlite3.DatabaseError, sqlite3's PARENT exception class, NOT a subclass of
OperationalError. T-3634 already added that exact message to
_STALE_CONNECTION_ERROR_SHAPES and _is_stale_or_corrupt_connection already
matches it by substring, but every T-3634/T-3700 stale-reconnect handler
(_run_with_stale_reconnect, _check_fingerprint_with_recovery,
_recover_fingerprint_connection, _reconnect_delay_for) and the sibling
test script itself only caught `except sqlite3.OperationalError`, so the
already-written matcher was never actually reachable for this shape -- a
NEW escape point T-3700 missed, not the same shape recurring from darwin
timing.

Fix (source, preferred per the mission -- no rerun/flaky marker needed):
widened every stale-reconnect catch clause (and the sibling test script's
own catch) from sqlite3.OperationalError to sqlite3.DatabaseError, so the
existing message-based shape matcher is reachable. _reconnect_delay_for
still re-raises unchanged on any message it does not recognize, so this
does not broaden what gets swallowed -- it only makes the already-declared
shape catchable. Also trimmed a docstring to keep
_run_with_stale_reconnect under ARCH001's 60-line threshold
(LANDPARITY002 flagged it as newly-crossed by the widened type
annotation's added prose).

Added two DETERMINISTIC regression tests (no CI-load timing dependency,
unlike the two-process stress test) that inject the bare DatabaseError
shape directly via monkeypatch and assert the retry loop recovers instead
of propagating:
- test_run_with_stale_reconnect_recovers_from_bare_database_error
- test_check_fingerprint_with_recovery_recovers_from_bare_database_error
Both also assert sqlite3.DatabaseError is genuinely not a subclass of
OperationalError, so the test's premise is checked, not assumed.

Evidence: the two new deterministic tests, plus the existing
test_two_processes_connecting_concurrently_never_see_no_such_table_meta
(strengthened only by the sibling script's widened catch, so a future
escape of this kind reports as an assertable ERRORS: line instead of a
silent crash).

frob:waive BUG002 reason="test_two_processes_connecting_concurrently_never_see_no_such_table_meta is the same nondeterministic race T-3634/T-3669/T-3700 waived: it manifests only under heavy PARALLEL CI load (run 33680767948, macOS), not deterministically at the parent commit, so no test can be bound that deterministically FAILS at the parent commit. CI is the true verifier for the race. The other two evidence ids ARE deterministic and were verified failing-then-passing locally against the pre-fix/post-fix code."

Local under-load: 15/15 sequential runs of the two-process stress test
green post-fix (loop.log); 6/6 of this class's tests green pre-land after
rebase onto origin/main (post_rebase.log, final.log). frob check --ticket
T-3706: ARCH001/LANDPARITY002 (newly-crossed-by-this-diff) fixed; remaining
errors (COV007, DEPR006, PRE001-cleared-by-sweep, TICK003, TICK011,
WAIVE011) are pre-existing/repo-wide, outside this ticket's scope.

Filed: none (no out-of-scope work found).

Gates: frob check --ticket T-3706 clean modulo the pre-existing repo-wide
errors above (all pre-date this diff); ARCH001/LANDPARITY002 fixed
in-scope.

### Changed
```
 src/frob/graph/cache.py        | 51 +++++++++++++++++++-------
 tests/unit/test_graph_cache.py | 83 +++++++++++++++++++++++++++++++++++++++++-
 tickets/T-3706/ticket.md       | 16 +++++++-
 3 files changed, 134 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_run_with_stale_reconnect_recovers_from_bare_database_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_check_fingerprint_with_recovery_recovers_from_bare_database_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 5 error(s), 4333 warning(s), 913 waived
- error-findings: COV007@.claude/hooks/frob-timeout-guard.py, DEPR006@frob-deprecated-baseline.lock.json, TICK003@tickets.md, TICK011@tickets.md, WAIVE011@frob-ratchet.lock.json
