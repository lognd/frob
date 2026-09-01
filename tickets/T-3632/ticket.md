---
id: T-3632
title: 'cache schema atomicity round 2: atomic rebuild + stale-conn fix'
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
## Description

Run 33472403980: T-3623's own regression test FAILED on BOTH POSIX legs:

  tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::
  test_two_processes_connecting_concurrently_never_see_no_such_table_meta
  E  AssertionError: sibling connect() loop observed a sqlite error:
     ... repeated "cache.connect: fingerprint None -> ... invalidating" +
     "schema None -> 4 rebuilding" cycles, ending with
     ERRORS:OperationalError('no such table: files')

So the schema-complete-before-visible fix covered `meta` but a sibling
still observes a db missing the `files` table -- schema creation is not
atomic as seen by a concurrent connector (and the log shows the two
processes thrashing each other's rebuilds: each sees fingerprint None,
invalidates, rebuilds, repeatedly). ALSO on ubuntu, a second failure
with the same root area:

  tests/test_gates.py::TestCoverageGate::test_waive002_end_to_end_via_run_gates
  E  sqlite3.InterfaceError: bad parameter or other API misuse
  at src/frob/graph/cache.py:1083

-- a NEW error class after T-3623's change (InterfaceError = misuse:
operating on a closed/invalid connection or bad binding), suggesting the
rename-quarantine/reopen path can leave a caller holding a stale
connection object.

## Plan

1. Make the WHOLE schema (all tables + meta + fingerprint row) exist
   before the db file becomes visible at the canonical path: build the
   complete db at a temp path, then a single atomic os.replace(). No
   connector may ever see a partial schema. Root cause found while
   investigating: `_apply_schema` (called by `_recreate_and_reapply`
   with `existing=None`) does its DROP TABLE / CREATE TABLE sequence
   IN PLACE on the live connection at the canonical path -- that is
   the exact non-atomic window the sibling test observes as "no such
   table: files".
2. Stop the mutual-rebuild thrash: two connectors that both decide
   "rebuild" must serialize on one exclusive lock and the loser must
   RE-CHECK (double-checked locking) instead of rebuilding again over
   the winner's fresh db.
3. Audit the reopen path for stale-connection reuse (the InterfaceError
   at cache.py:1083): any cached/module-level connection must be
   invalidated when _recreate replaces the file; callers get a fresh
   connect. Found: `connect()`'s closure over `conn` passed to
   `_with_lock_retry` can retry against a stale/closed connection
   object if a recreate happened inside the retried op.
4. The existing two-process regression test is the acceptance bar -- it
   must pass 5x consecutively locally AND its assertion should also
   catch 'no such table: files' (it does, via the ERRORS: channel --
   keep that). Add a stale-connection unit test for item 3.

Scope: src/frob/graph/cache.py + tests/unit/test_graph_cache.py.
CRITICAL: these two failures are currently the ONLY POSIX suite
failures; this ticket IS the release path.
