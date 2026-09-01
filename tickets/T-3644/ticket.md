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