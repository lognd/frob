---
id: T-3794
title: skipif win32 for POSIX-only fs-notify test
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
- tests/test_serve_daemon.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 waiver: win32-only defect, no Linux repro possible'
  actor: logan
  at: '2026-09-04'
  old_length: 137
  new_length: 512
evidence:
- tests/test_serve_daemon.py::TestWatchThreadNotifiesVerifyWorker::test_fs_change_notifies_the_cached_verify_worker
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 drain: test_fs_change_notifies_the_cached_verify_worker relies on ThreadingUnixStreamServer/AF_UNIX, POSIX-only. Add skipif(win32).

frob:waive BUG002 reason="win32-only defect confirmed via winrun; no Linux parent-commit repro -- the test already passes on Linux both before and after the skipif; the fix only changes behavior on Windows, where the unmodified test failed with 'daemon never became reachable' due to socketd's POSIX-only ThreadingUnixStreamServer transport (T-2961), confirmed via winrun"