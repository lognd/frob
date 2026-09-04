---
id: T-3774
title: 'ty win32 error: os.major/os.minor unnarrowed after T-3768 replaced the sys.platform
  assert with skipif'
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
- tests/system/test_fleet_status_ground_truth.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/system/test_fleet_status_ground_truth.py
  reason: restore ty platform-narrowing for os.major/os.minor
  actor: logan
  at: '2026-09-04'
body_changes:
- mode: append
  reason: 'BUG002: type-check-only fix, no runtime behavior change; supply no-behavior-change
    per land guidance

    '
  actor: logan
  at: '2026-09-04'
  old_length: 0
  new_length: 472
evidence:
- tests/system/test_fleet_status_ground_truth.py::TestLandLockHolderClaim::test_must_fire_the_true_holder_among_waiters
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:no-behavior-change reason="Type-check-only fix: adds an in-body assert sys.platform != win32 (plus a comment) to restore ty platform-narrowing for the POSIX-only os.major/os.minor calls. No runtime behavior change on any platform (the assert is always-true where the test runs; the test is skipif-skipped on win32). The bound test passes at main and at the fix; the defect was a static ty unresolved-attribute under win32 analysis, which has no pytest reproduction."