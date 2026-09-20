---
id: T-3669
title: 'cache round 6: reopen the connection handle at the canonical path instead
  of retrying a replaced-away inode'
state: done
kind: bug
origin: human
created: '2026-09-01'
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
scope_changes:
- op: add
  glob: tests/unit/test_graph_build_lock.py
  reason: 'SCOPE002: cache.py::connect and the lock helpers are covered by this file''s
    two-process test, T-3669''s acceptance evidence'
  actor: logan
  at: '2026-09-01'
body_changes:
- mode: append
  reason: condense atomicity-saga history into T-3669 body
  actor: logan
  at: '2026-09-19'
  old_length: 3074
  new_length: 4623
evidence:
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_replaced_away_handle_is_reopened_before_the_next_read
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_fingerprint_read_after_a_replace_lands_on_the_live_file
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_store_file_data_after_a_replace_lands_on_the_live_file
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_lock_retry_lets_a_readonly_fault_escape_to_the_reopen_layer
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_readonly_database_is_classified_as_a_handle_fault
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_identity_changes_after_os_replace
- tests/unit/test_graph_cache.py::TestHandleIdentity::test_live_handle_is_not_reopened
- tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::test_two_processes_connecting_concurrently_never_see_no_such_table_meta
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
=== cache round 6: darwin two-process readonly-database persists past T-3654's deadline backoff ===

Run 33529632605 macOS (ubuntu leg PASSED this test the same run; the
pushed sha 59c163e8f INCLUDES T-3654's deadline backoff, so round 5 is
measured insufficient on darwin):

  tests/unit/test_graph_cache.py::TestRecreateNeverExposesASchemaIncompleteDb::
  test_two_processes_connecting_concurrently_never_see_no_such_table_meta
  sibling loop observed ~20 repeated cycles of
    "cache.connect: fingerprint None -> '<pkg fingerprint>' ...
     invalidating cached rows"
  ending with ERRORS:CacheLocked('attempt to write a readonly database')

READ THE LOG SHAPE CAREFULLY -- two distinct defects are visible:
1. MUTUAL-REBUILD THRASH IS BACK (or was never fully fixed on darwin):
   both processes repeatedly see fingerprint None and invalidate/rebuild
   over each other, ~20 cycles. T-3632's double-checked locking was
   supposed to make the loser RE-CHECK after the winner's rebuild and
   accept the fresh db. On darwin it keeps thrashing: after a rebuild
   completes, the sibling STILL reads fingerprint None. Hypothesis: the
   fingerprint read happens on a connection opened BEFORE the winner's
   os.replace (stale inode -- darwin keeps the old file open), so the
   loser reads the pre-replace empty db forever; each of its own
   rebuilds then swaps the file again, re-invalidating the winner.
   Fix direction: after acquiring the rebuild lock and BEFORE deciding
   to rebuild, close and REOPEN the connection at the canonical path,
   then re-read the fingerprint; only rebuild if still stale from the
   FRESH connection. Same reopen-before-recheck in the retry path.
2. The terminal error is CacheLocked('attempt to write a readonly
   database') -- the writer path opened a connection that darwin
   considers readonly (likely a connection to a replaced-away inode, or
   the readonly fallback connect path being reused for a write).
   Audit which connect produced the handle used for the write and make
   the readonly-shape error trigger the same close+reopen+recheck, not
   just a same-handle retry (T-3654 retries the OPERATION but keeps the
   STALE HANDLE -- that is why deadline backoff did not help: every
   retry reuses the doomed connection).

Acceptance: the two-process test 10x consecutively locally AND note CI
macOS is the true verifier (5 prior rounds passed locally and failed on
darwin CI; local passes are necessary, not sufficient). Add a unit test
that a connection surviving an os.replace is detected and REOPENED on
the next fingerprint read (simulate with an explicit replace between
connect and read).
History: T-3607 (quarantine-rename), T-3623 (schema-complete-before-
visible), T-3632 (atomic temp-build + double-checked locking), T-3634
(disk-I/O reconnect retry), T-3644 (WAL retirement + TRUNCATE +
readonly-db retry match), T-3654 (deadline backoff) -- all landed, all
insufficient on darwin. Round 6 must fix the HANDLE lifecycle, not add
more retries.
Scope: src/frob/graph/cache.py + tests/unit/test_graph_cache.py.

<!-- narrative-moved:src/frob/graph/cache.py:943:T-3669 -->
frob:ticket T-3669
Round 6 of the cache-atomicity saga. Every prior round (T-3607 quarantine
-rename, T-3623 schema-complete-before-visible, T-3632 atomic temp-build
+ double-checked locking, T-3634 disk-I/O reconnect, T-3644 WAL
retirement, T-3654 deadline backoff) treated the symptom on the SAME
connection object. The defect they all missed is a HANDLE LIFECYCLE one:
`os.replace` publishes a NEW inode at the canonical path, and a
`sqlite3.Connection` opened before that replace stays bound to the OLD,
now-unlinked (or quarantined) inode forever. On darwin such a handle
reads the pre-replace state indefinitely -- so a sibling keeps seeing
`fingerprint None`, re-invalidates, republishes, and the two processes
thrash rebuilds over each other (~20 cycles, run 33529632605) -- and a
WRITE through it surfaces as `attempt to write a readonly database`,
which every retry loop then retried ON THE SAME DOOMED HANDLE. The fix
is to make "is my handle still bound to the file at the canonical path?"
a cheap, explicit check taken BEFORE every fingerprint read and before
every retried operation, and to make the readonly shape reopen rather
than retry. `id(conn)` keys this map because `sqlite3.Connection`
supports neither weak references nor attribute assignment; entries are
dropped in `_close_conn`, and an id collision is harmless either way (a
stale entry that differs from the live inode only causes one extra
correct reopen; one that matches it describes the same file anyway).