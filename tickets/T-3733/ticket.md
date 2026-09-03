---
id: T-3733
title: 'cache: InterfaceError escapes stale-reconnect handlers (round 9)'
state: in-progress
kind: bug
origin: human
created: '2026-09-03'
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_run_with_stale_reconnect_recovers_from_interface_error
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_check_fingerprint_with_recovery_recovers_from_interface_error
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_is_stale_or_corrupt_connection_matches_interface_error_by_type
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 33729699769 (macOS): tests/gates_suite/test_waive.py::TestWaive004DegradedRunGuard::test_healthy_run_below_threshold_still_deletes
failed with sqlite3.InterfaceError: bad parameter or other API misuse.

Root cause: round 8 (T-3706) widened stale-reconnect catch clauses from
sqlite3.OperationalError to sqlite3.DatabaseError to catch bare-DatabaseError
torn reads. But sqlite3.InterfaceError is NOT a subclass of DatabaseError --
both are siblings under sqlite3.Error. A stale/closed connection raising
InterfaceError still escapes every stale-reconnect handler in
src/frob/graph/cache.py.

Fix: widen the stale-reconnect catch clauses (and _is_stale_or_corrupt_connection)
to sqlite3.Error (or explicitly add InterfaceError/ProgrammingError) so this
shape routes through reopen-at-canonical retry like every other stale shape.
Keep bounded retry + deadline; past deadline raise typed CacheError, not the
raw sqlite exception. Add a deterministic regression test (monkeypatch a
handler to raise sqlite3.InterfaceError once, assert reopen-retry recovers).