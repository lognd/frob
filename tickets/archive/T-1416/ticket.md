---
id: T-1416
title: 'cache.db recreate still fires on a concurrency IntegrityError: UNIQUE constraint
  on meta.key destroys a shared cache'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/cache.py
- tests/test_graph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_graph.py::TestSchemaLockContentionRecovery::test_concurrent_meta_key_integrity_error_retries_instead_of_recreating
- tests/test_graph.py::TestSchemaLockContentionRecovery::test_non_meta_key_integrity_error_still_recreates
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files
designated_repro_test: null
acceptance:
- text: GIVEN two processes applying the cache schema concurrently WHEN one hits UNIQUE
    constraint failed on meta.key THEN it re-reads the schema version and proceeds,
    and no recreate occurs
  evidence:
  - tests/test_graph.py::TestSchemaLockContentionRecovery::test_concurrent_meta_key_integrity_error_retries_instead_of_recreating
- text: GIVEN a genuinely corrupt cache.db WHEN the schema cannot be applied THEN
    the recreate path still runs exactly as today, proven by a regression test
  evidence:
  - tests/test_graph.py::TestSchemaLockContentionRecovery::test_non_meta_key_integrity_error_still_recreates
- text: GIVEN the full suite under pytest -n 4 WHEN it runs THEN tests/system/test_cli_native_missing.py
    does not fail with no such table
  evidence:
  - tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files
threat: null
component: null
---
T-1239 landed a fix for graph cache.db lock contention (splitting the except so a locked OperationalError polls and re-reads the schema version instead of triggering the destructive delete-and-recreate). That fix is real and its tests pass. But the failure class it targets is NOT gone: a different corruption path in the same recovery code still fires under parallel load.

Measured on main 2026-08-01, during a make coverage run (pytest -n 4), from .frob/last-coverage-run.log:

    WARNING: cache.connect: /tmp/.../repo/.frob/cache.db failed schema application, recreating: UNIQUE constraint failed: meta.key
    ERROR: main: unhandled exception during dispatch: no such table: meta
    frob: no such table: meta

So the sequence is: schema application hits "UNIQUE constraint failed: meta.key" (an IntegrityError, not the OperationalError T-1239 carved out), that is treated as genuine corruption, the recreate path runs, and a concurrent reader then finds "no such table: meta" mid-recreate. Same shape as the original incident, one exception class over.

"UNIQUE constraint failed: meta.key" is itself the signature of two processes applying the schema concurrently -- both insert the same meta row. It is a concurrency symptom, not corruption, and destroying the database in response is what turns a recoverable race into a hard failure for every other process sharing that cache.

Reproduction: tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files fails under pytest -n 4 and PASSES standalone (verified: both this and the T-1240 test pass serially in 31s). So it is parallelism, not a code defect in the test's own subject.

Why this matters now, beyond the flake: make coverage runs the suite under xdist and fails at exit 2 when any test fails, leaving coverage.xml unwritten. TEST005 is roughly 80 percent of the repo's remaining warnings and is the dominant unknown for the v1.0.0 zero-warning bar. Until the suite can complete under parallelism, that number cannot be measured at all -- the release gate is blocked on this, not on the coverage work itself.

Fix direction, not prescriptive: treat IntegrityError on the meta table during schema application the same way T-1239 already treats a locked OperationalError -- as evidence another process got there first, so re-read the schema version and proceed rather than recreate. More generally, the recreate path should require positive evidence of corruption, never merely "an exception occurred while applying the schema". Recreating a shared cache is destructive to every concurrent reader and should be the last resort, not the default handler.

Add a regression test that exercises concurrent schema application (two processes or two threads racing connect on a fresh cache.db) and asserts no recreate occurs and no reader observes a missing table. T-1239's own tests spy on _recreate; extend that pattern.