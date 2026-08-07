## Done report

A "UNIQUE constraint failed: meta.key" IntegrityError during schema
application is two processes racing the same migration, not corruption:
both raced past the existing != _SCHEMA_VERSION check, both DROP/CREATE
TABLE'd, and both tried to INSERT the schema_version row into meta; the
loser's INSERT hits the UNIQUE constraint. Since IntegrityError subclasses
DatabaseError, it previously fell into the same recreate-on-any-
DatabaseError bucket T-1239 already fixed for lock contention, destroying
a cache another process just finished writing and leaving a concurrent
reader to observe "no such table: meta" mid-recreate.

_apply_schema_with_recovery now catches sqlite3.IntegrityError before the
general DatabaseError branch, narrowed to the meta.key UNIQUE-constraint
signature (_is_concurrent_meta_key_race), and re-reads the schema version
and retries instead of recreating -- same recovery shape T-1239 already
uses for a locked OperationalError. Any other IntegrityError (a real
constraint violation not matching that signature) still recreates
unchanged. The shared poll-then-reread and recreate-then-reapply steps
were pulled into _poll_and_reread/_recreate_and_reapply helpers to keep
_apply_schema_with_recovery under the ARCH001 60-line threshold after
adding the new branch.

Verified per the coordinator's exact repro command:
tests/system/test_cli_native_missing.py and tests/system/test_frob_self_model.py
now pass together under pytest -n 4 (7 passed, 34s) -- both were reported
failing/crashing on main under xdist load.

### Changed
```
 src/frob/graph/cache.py | 120 +++++++++++++++++++++++++++++++-----------------
 tests/test_graph.py     |  90 ++++++++++++++++++++++++++++++++++++
 tickets.md              |  15 ++++--
 3 files changed, 180 insertions(+), 45 deletions(-)
```

### Evidence
- `tests/test_graph.py::TestSchemaLockContentionRecovery::test_concurrent_meta_key_integrity_error_retries_instead_of_recreating` (pytest node id, verified passing when recorded)
- `tests/test_graph.py::TestSchemaLockContentionRecovery::test_non_meta_key_integrity_error_still_recreates` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 457 warning(s), 697 waived
- error-findings: none (measured, zero errors)
