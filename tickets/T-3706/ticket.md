---
id: T-3706
title: 'cache: sibling connect loop crashes on bare sqlite3.DatabaseError (round 8)'
state: done
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
- tests/unit/test_graph_cache.py
- tests/unit/test_graph_build_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-3706 round 8: waiving BUG002 for the shared nondeterministic two-process
    stress test, same rationale as T-3700'
  actor: logan
  at: '2026-09-02'
  old_length: 434
  new_length: 1012
evidence:
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_run_with_stale_reconnect_recovers_from_bare_database_error
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_check_fingerprint_with_recovery_recovers_from_bare_database_error
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Round 8 of the cache two-process saga (T-3607/T-3623/T-3632/T-3634/T-3644/T-3654/T-3669/T-3700). Run 33680767948 macOS: sibling crashed silently on a bare sqlite3.DatabaseError ('file is not a database' shape) that every T-3634/T-3700 stale-reconnect handler only catches as sqlite3.OperationalError -- DatabaseError is the PARENT class, not a subclass, so it escapes uncaught. Fix: broaden the catch clauses to sqlite3.DatabaseError.

frob:waive BUG002 reason="The regression tests for T-3706 are deterministic (test_run_with_stale_reconnect_recovers_from_bare_database_error / test_check_fingerprint_with_recovery_recovers_from_bare_database_error inject the bare DatabaseError shape directly), but the third bound test (the two-process stress test) is the same nondeterministic race T-3700 waived under BUG002: it manifests only under heavy PARALLEL CI load (run 33680767948, macOS), not a deterministic failure at the parent commit. CI is the true verifier for the race. Same spirit as T-3634/T-3669/T-3700."