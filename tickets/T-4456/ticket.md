---
id: T-4456
title: 'Windows: T-4454''s _recreate publish hits WinError 5 (os.replace over an open
  handle), test_path_never_absent_during_recreate fails'
state: queued
kind: bug
origin: agent
created: '2026-09-13'
priority: critical
parent: T-3505
tier: ticket
sprint: v0.531.0
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
CI run 34739935923 (head b69c67b1b, includes T-4454), Windows leg: the NEW deterministic test tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_path_never_absent_during_recreate fails with PermissionError: [WinError 5] Access is denied: '...\cache.db.new-9080-d0f88287' -> '...\cache.db'. T-4454 made _recreate keep the old inode reachable (hard link for the quarantine copy) and publish the rebuilt db over the path with os.replace; on win32, os.replace onto a file that still has an open sqlite handle (this process's own connection, or the hard-linked quarantine copy sharing the same file object) is refused with WinError 5 -- the same class T-4402 fixed for the ordinary rebuild path ("graph cache rebuild fails on Windows: os.replace onto open sqlite handle"). Read tickets/T-4402/done-report.md for the recipe that already works (close the handle before replace, retry on WinError 5/32 with backoff, or copy-then-truncate instead of replace on win32) and apply it in _recreate/_quarantine_main_db/_replace_with_retry; keep the POSIX guarantee from T-4454 (a file exists at path at every instant). The sibling test test_sibling_reader_survives_concurrent_recreate carries `@_WIN32_NO_REPLACE_OVER_OPEN_HANDLE`; the new test must either pass on win32 with the fix or carry the same documented marker with a reason -- prefer the fix. ACCEPTANCE: (1) the two T-4454 tests and TestLockedDbNeverRebuilds pass on the winrun mirror (measure), and still pass on Linux; (2) macOS/ubuntu behaviour unchanged (loop the concurrent-reader test 10x on Linux); (3) Windows CI leg green on this node id on the next push. Sprint v0.531.0 (CI green blocker).
