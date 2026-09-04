---
id: T-3769
title: land-lock msvcrt-backend round-trip test crashes on real Windows
state: in-progress
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/ticket_land_suite/test_land_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'waive BUG002: win32-only repro (missing fcntl module), confirmed via winrun
    not a Linux parent-commit'
  actor: logan
  at: '2026-09-04'
  old_length: 696
  new_length: 1122
evidence:
- tests/ticket_land_suite/test_land_lock.py::TestLandLockPlatformBackends::test_windows_backend_round_trips
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
test_windows_backend_round_trips (TestLandLockPlatformBackends) is designed to skip itself on real win32 (the fake's locking() checks sys.platform=='win32' and calls pytest.skip), but the test body does 'import fcntl as _real_fcntl' UNCONDITIONALLY before that skip check is ever reached -- fcntl does not exist on Windows at all, so the import raises ModuleNotFoundError before pytest.skip runs. Confirmed via winrun on the Windows mirror (Python 3.12.10): ModuleNotFoundError: No module named 'fcntl' at tests/ticket_land_suite/test_land_lock.py:337.

Fix: move the win32 platform check to the very top of the test (before importing fcntl) so it skips cleanly instead of crashing on the import.



frob:waive BUG002 reason="win32-only defect (real Windows lacks the fcntl module entirely); the designated evidence test passes at the parent commit on this Linux checkout because fcntl exists there and the buggy unconditional import never fails. Repro is the Windows CI/interop leg, confirmed via winrun (Python 3.12.10): before the fix it crashed with ModuleNotFoundError, after the fix it skips cleanly (exitstatus=0)."