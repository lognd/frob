## Done report

Root cause: src/frob/graph/cache.py::connect calls _check_fingerprint(conn, path)
directly, unlike every other cache write path (store_file_data, set_root,
touch_file_stat, connect_readonly, and the schema-application DDL), which
already go through _with_lock_retry (T-1423). _check_fingerprint's own
fingerprint-mismatch invalidation is a real write (DELETE the derived
tables, upsert the new fingerprint), so a lock hit there crashed connect()
-- and everything above it -- unhandled, exactly the "database is locked" /
"unhandled exception during dispatch" crash T-3130 measured under ordinary
concurrent frob check load.

Fix: route the _check_fingerprint call through the existing
_with_lock_retry helper, identical in shape to the other four write paths.
_check_fingerprint is idempotent under retry (first statement is a SELECT;
a lock error on a later write means nothing committed yet, so re-running
the whole function is safe).

Test-first (BUG002): added
test_connect_retries_a_transient_lock_during_fingerprint_check, monkeypatching
_check_fingerprint to raise sqlite3.OperationalError("database is locked")
twice before succeeding, mirroring the existing
test_retries_then_succeeds_past_a_transient_lock pattern one level up the
call stack (at connect(), the actual public surface frob check calls).
Manually confirmed this test FAILS with a bare sqlite3.OperationalError at
the parent commit (before the fix) and PASSES after. `--designate-repro`
could not be used to record this mechanically: the test and fix were
committed together in this worktree (same as every squashed land), so no
ancestor commit has the test without the fix -- the exact T-2025
limitation the tooling itself documents.

T-3131 connection: does NOT explain T-3131's one-off. Checked directly:
src/frob/tickets/_reporting.py and src/frob/app/ticket_runner/_close_cmd.py
(the disclosure-guard code path T-3131 describes) import nothing from
frob.graph or frob.graph.cache -- ticket bodies are read from tickets.md/
ticket.md via frob.tickets._store, an entirely separate subsystem from the
graph sqlite cache this ticket fixes. No plausible mechanism connects
them; T-3131 remains unconfirmed and should stay open on its own.

### Changed
```
 docs/modules/graph.md    |  8 ++++++++
 src/frob/graph/cache.py  | 14 +++++++++++++-
 tests/test_graph_lock.py | 36 ++++++++++++++++++++++++++++++++++++
 tickets/T-3130/ticket.md |  6 +++++-
 4 files changed, 62 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_graph_lock.py::TestCacheLockRetry::test_connect_retries_a_transient_lock_during_fingerprint_check` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
