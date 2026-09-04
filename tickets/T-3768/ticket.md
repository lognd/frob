---
id: T-3768
title: skip win32-only PID-1-liveness and proc-locks tests
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
- tests/unit/test_check_admission.py
- tests/system/test_fleet_status_ground_truth.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: add BUG002 waiver
  actor: logan
  at: '2026-09-04'
  old_length: 461
  new_length: 583
evidence:
- tests/unit/test_check_admission.py::TestAdmissionRegistryAnchor::test_two_worktrees_see_each_others_markers
- tests/system/test_fleet_status_ground_truth.py::TestLandLockHolderClaim::test_must_fire_the_true_holder_among_waiters
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TestAdmissionRegistryAnchor.test_two_worktrees_see_each_others_markers assumes PID 1 always exists and is alive (a POSIX init-pid assumption); pid_alive(1) is not guaranteed True on win32 so the liveness-count-== 2 assertion is not portable. TestLandLockHolderClaim.test_must_fire_the_true_holder_among_waiters already self-asserts sys.platform != win32 and uses os.major/os.minor plus a /proc/locks fixture; convert the failing self-assert into a clean skipif.

frob:waive BUG002 reason="win32-only skip; POSIX-primitive dependency not reproducible from a Linux parent-commit repro"