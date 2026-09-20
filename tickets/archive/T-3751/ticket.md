---
id: T-3751
title: 'win32 test portability (fcntl class): tests importing fcntl fail on Windows;
  skipif POSIX-only lock tests'
state: done
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
- tests/test_coverage_wait_shared.py
- tests/test_serve_socket.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_coverage_wait_shared.py
  reason: these tests simulate the Windows msvcrt lock backend on POSIX via real fcntl.flock;
    on real Windows they must skipif since the real msvcrt backend runs instead
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/test_serve_socket.py
  reason: these tests simulate the Windows msvcrt lock backend on POSIX via real fcntl.flock;
    on real Windows they must skipif since the real msvcrt backend runs instead
  actor: logan
  at: '2026-09-04'
evidence:
- tests/test_coverage_wait_shared.py::TestCoverageLockPlatformBackends::test_windows_backend_round_trips
- tests/test_serve_socket.py::TestAcquireSingletonLockPlatformBackends::test_windows_backend_round_trips
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

frob:waive BUG002 reason="the defect is Windows-only: these tests fail (ModuleNotFoundError: fcntl) only on win32. The fix marks them skipif(sys.platform=='win32'). On the Linux land host fcntl exists and both tests PASS at parent and fix alike, so there is no Linux repro; the real before/after was verified on a live Windows run via the local mirror (they now SKIP instead of erroring). Same spirit as the win32 CI-config BUG002 waives -- a platform-only defect the Linux suite cannot reproduce."