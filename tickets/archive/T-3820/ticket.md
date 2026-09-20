---
id: T-3820
title: graph cache os.replace unguarded on Windows [WinError 5] under concurrent access
  -- retry-on-PermissionError + un-skip the transient T-3781 tests
state: done
kind: bug
origin: human
created: '2026-09-05'
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
scope_changes:
- op: add
  glob: src/frob/graph/cache.py
  reason: add bounded retry-on-PermissionError/OSError around os.replace publish primitive
  actor: logan
  at: '2026-09-05'
- op: add
  glob: tests/unit/test_graph_cache.py
  reason: un-skip transient T-3781 tests; narrow skip to persistent-handle cases
  actor: logan
  at: '2026-09-05'
body_changes:
- mode: append
  reason: bind TestReplaceWithRetry evidence, BUG002 win32-only waiver, and per-test
    (B) classification of the T-3781 skips
  actor: logan
  at: '2026-09-05'
  old_length: 0
  new_length: 1429
evidence:
- tests/unit/test_graph_cache.py::TestReplaceWithRetry::test_transient_permission_error_is_retried_then_succeeds
- tests/unit/test_graph_cache.py::TestReplaceWithRetry::test_persistent_permission_error_is_reraised_after_the_deadline
- tests/unit/test_graph_cache.py::TestReplaceWithRetry::test_posix_happy_path_replaces_on_the_first_attempt
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

## Evidence (T-3820)

frob:tests tests/unit/test_graph_cache.py::TestReplaceWithRetry.test_transient_permission_error_is_retried_then_succeeds
frob:tests tests/unit/test_graph_cache.py::TestReplaceWithRetry.test_persistent_permission_error_is_reraised_after_the_deadline
frob:tests tests/unit/test_graph_cache.py::TestReplaceWithRetry.test_posix_happy_path_replaces_on_the_first_attempt

frob:waive BUG002 reason="win32-only concurrency defect confirmed via winrun; no Linux parent-commit repro (os.replace never fails over an open handle on POSIX). The transient-fix retry logic is proven cross-platform by TestReplaceWithRetry (monkeypatched os.replace) on both Linux and winrun; the 6 T-3781/T-3820 tests model the unsupported persistent-handle case and stay skipped, accounted by a frob:invariant on cache.py."

## Classification of the 6 T-3781 tests (winrun-confirmed WITH the fix)

All 6 remain (B) persistent-by-design on Windows -- none pass even with
_replace_with_retry in place, because each keeps a handle open on the
destination across the whole publish (five hold a single reader/conn open
persistently; test_two_processes saturates the path with a zero-gap sibling
connect/close loop so no retry window opens). The production retry fixes the
realistic transient shape (gate worker opening+closing around each access,
leaving gaps), proven by a minimal winrun repro and TestReplaceWithRetry on
Linux and Windows.