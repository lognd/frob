---
id: T-3623
title: 'T-3607 fallout: fresh-rebuilt cache db visible without schema'
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: critical
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33466891764 macOS, the leg's ONLY suite failure:

  tests/test_coverage_wait_shared.py::TestWorktreeLock::
  test_uses_daemon_lease_when_daemon_up
  E  sqlite3.OperationalError: no such table: meta
  at src/frob/graph/cache.py:377

T-3607 (landed fb598a6cb) changed _recreate from unlink-in-place to
quarantine-rename + fresh db creation. A reader/second connection can
now observe the freshly created db file BEFORE the schema (meta table)
is initialized in it -- previously the "unreadable db, rebuilding"
handler caught this shape (the WARNING "no such table: meta, rebuilding"
exists at cache.connect line ~315), but line 377's code path raises
instead of routing through that rebuild handler, or the handler itself
now races the renamed-away file. Fix directions:
1. Create the fresh db at a temp path, initialize the FULL schema, then
   atomically rename INTO place -- a visible db file is always
   schema-complete (same atomicity doctrine as T-3607 itself).
2. Ensure every read path that can hit "no such table: meta" routes
   through the connect-time rebuild handler rather than raising.
3. Regression test: two processes, one triggers _recreate while the
   other connects in a loop; assert no OperationalError escapes.
Scope: src/frob/graph/cache.py + tests/unit/test_graph_cache.py.
This is release-path: it is the macOS leg's only remaining suite
failure and is a race (can hit any leg).
