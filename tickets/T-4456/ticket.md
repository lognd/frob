---
id: T-4456
title: 'Windows: T-4454''s _recreate publish hits WinError 5 (os.replace over an open
  handle), test_path_never_absent_during_recreate fails'
state: done
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
body_changes:
- mode: append
  reason: 'record BUG002 waiver: defect win32-only, repro measured off-host via winrun'
  actor: logan
  at: '2026-09-13'
  old_length: 1672
  new_length: 2781
evidence:
- tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_path_never_absent_during_recreate
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34739935923 (head b69c67b1b, includes T-4454), Windows leg: the NEW deterministic test tests/unit/test_graph_cache.py::TestRecreateConcurrentReaderSurvives::test_path_never_absent_during_recreate fails with PermissionError: [WinError 5] Access is denied: '...\cache.db.new-9080-d0f88287' -> '...\cache.db'. T-4454 made _recreate keep the old inode reachable (hard link for the quarantine copy) and publish the rebuilt db over the path with os.replace; on win32, os.replace onto a file that still has an open sqlite handle (this process's own connection, or the hard-linked quarantine copy sharing the same file object) is refused with WinError 5 -- the same class T-4402 fixed for the ordinary rebuild path ("graph cache rebuild fails on Windows: os.replace onto open sqlite handle"). Read tickets/T-4402/done-report.md for the recipe that already works (close the handle before replace, retry on WinError 5/32 with backoff, or copy-then-truncate instead of replace on win32) and apply it in _recreate/_quarantine_main_db/_replace_with_retry; keep the POSIX guarantee from T-4454 (a file exists at path at every instant). The sibling test test_sibling_reader_survives_concurrent_recreate carries `@_WIN32_NO_REPLACE_OVER_OPEN_HANDLE`; the new test must either pass on win32 with the fix or carry the same documented marker with a reason -- prefer the fix. ACCEPTANCE: (1) the two T-4454 tests and TestLockedDbNeverRebuilds pass on the winrun mirror (measure), and still pass on Linux; (2) macOS/ubuntu behaviour unchanged (loop the concurrent-reader test 10x on Linux); (3) Windows CI leg green on this node id on the next push. Sprint v0.531.0 (CI green blocker).



frob:waive BUG002 reason="the defect is win32-only (os.replace refuses to rename onto a path with an open handle lacking FILE_SHARE_DELETE); check-repro runs the designated test at the parent commit on this (Linux) host, where os.replace never fails on an open destination handle, so the test PASSED_AT_PARENT here regardless of the fix -- confirmatory-only by construction here, not by omission. The actual fail-before/pass-after repro was measured on the winrun Windows mirror: before the fix (patch reverted), test_path_never_absent_during_recreate FAILED with PermissionError: [WinError 5] Access is denied on the os.replace(tmp_path, path) call inside _recreate's publish, matching CI run 34739935923's traceback exactly; after the fix (win32 overwrite-in-place fallback in _replace_with_retry), the same test PASSED (TestRecreateConcurrentReaderSurvives + TestLockedDbNeverRebuilds: 6 passed, 1 skipped -- the sibling-process test's own documented _WIN32_NO_REPLACE_OVER_OPEN_HANDLE skip, unaffected by this fix). Full tests/unit/test_graph_cache.py: 51/51 passed on the winrun mirror and on Linux."