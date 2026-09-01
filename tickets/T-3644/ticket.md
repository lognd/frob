---
id: T-3644
title: 'cache SIGBUS round 4: retire WAL journal mode on graph cache'
state: in-progress
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
- tests/unit/test_graph_build_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'waive BUG002: SIGBUS is a nondeterministic OS-signal crash, not locally
    reproducible as a test failure'
  actor: logan
  at: '2026-09-01'
  old_length: 2204
  new_length: 3667
evidence:
- tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope::test_two_processes_never_commit_to_the_same_cache_concurrently
- tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_connect_after_forced_schema_rebuild_returns_a_fresh_live_connection
- tests/unit/test_graph_cache.py::TestConnectNeverReturnsAStaleConnection::test_recreate_closed_connection_raises_a_clean_programming_error_not_interface_error
- tests/test_graph.py::TestConcurrentCache::test_connect_on_current_schema_does_not_block_on_a_held_write_lock
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 33491468339, BOTH POSIX legs: worker killed by 'Fatal Python error: Bus error' running tests/unit/test_graph_build_lock.py::TestBuildGraphLockScope::test_two_processes_never_commit_to_the_same_cache_concurrently (WORKER-CRASH-REPORT named it; the T-3608 watchdog then aborted the session loudly -- working as designed).

History: T-3607 (rename-quarantine, never unlink live sidecars), T-3623 (schema-complete-before-visible), T-3632 (atomic os.replace + double-checked locking + stale-conn fix), T-3634 (disk-I/O-error reconnect retry) -- four rounds of hardening and a SIGBUS still kills workers. The remaining hole is STRUCTURAL: in WAL mode every connection mmaps the -shm wal-index; ANY cross-process sequence that replaces/recovers the db while a sibling holds that mapping (SQLite's own WAL recovery truncating -shm included) can SIGBUS the sibling at the OS level -- unreachable by python-level error handling (it is a fatal signal, not an exception). This run's crash is in the BUILD-LOCK test (build_graph path), not the test_graph_cache.py test the prior rounds targeted -- the class is broader than _recreate.

Fix: retire WAL for this cache. PRAGMA journal_mode=DELETE (or TRUNCATE) on every cache connection -- no -shm, no mmap, SIGBUS class structurally eliminated. Keep ALL the atomic-rebuild machinery from rounds 1-3 (still correct and needed). The cache is a content-addressed artifact/derived-state store whose writes already retry through contended-lock helpers (T-1423) -- WAL's concurrent-reader benefit is not worth this class.

Measure before/after: the two-process tests in test_graph_cache.py AND test_graph_build_lock.py 5x each locally; xdist suite wall-time delta on a scoped package (report the number; if the full-suite cost is severe, say so in the Done report rather than silently accepting it -- but correctness beats perf here). Check journal-mode interplay with connect()'s existing pragmas and the readonly connect path. Note the existing _open() comment: rollback-journal mode previously timed out even at 30s under 4 parallel builders -- TRUNCATE mode may avoid that (no journal file create/delete per txn) where DELETE would not; measure and pick accordingly.


frob:waive BUG002 reason="the defect is a SIGBUS -- a fatal OS signal delivered to a sibling process/thread whose sqlite connection has the WAL -shm wal-index mmap'd, raised by a racing cross-process db replace/recover. It killed a worker in CI (run 33491468339) under real multi-process contention; it is not deterministically reproducible as a local test failure (WSL/Linux here never hit it directly, and the designated evidence test already PASSES at main under WAL for the same reason -- the SIGBUS is a rare timing-and-environment-dependent OS-level fault, not a python-visible exception a test assertion can pin pass/fail across). The fix (retire WAL for TRUNCATE) structurally eliminates the WAL -shm mmap the crash class depends on, which is a property of the journal mode, not of any one call path a mutation test could kill. The bound evidence instead pins: (1) the SAME-PROCESS two-thread build_graph race this journal-mode switch's own follow-on fix (the in-process write lock) was needed to keep passing under TRUNCATE -- this is the test that WAS observably flaky (~20-40% failing) under TRUNCATE-without-the-lock during development, and is 10/10 clean with the full fix, so it does discriminate the fix's own follow-on correctness even though it cannot discriminate WAL-vs-TRUNCATE's SIGBUS-safety itself; (2) T-0232's pinned no-block-behind-a-held-write invariant, which the first (too-broad) lock design broke and the landed design does not."