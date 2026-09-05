---
id: T-3795
title: skip sigkill worker crash repro test on win32 (no SIGKILL)
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
- tests/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'waive BUG002: win32-only skipif fix, no linux repro possible'
  actor: logan
  at: '2026-09-04'
  old_length: 117
  new_length: 215
evidence:
- tests/test_coverage.py::TestWorkerCrashSignatureRealSubprocess::test_sigkill_worker_crash_is_a_real_repro
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
signal.SIGKILL does not exist on win32; skipif(win32) the real-subprocess sigkill repro test. Part of win32 CI drain.

frob:waive BUG002 reason="win32-only defect confirmed via winrun; no Linux parent-commit repro"