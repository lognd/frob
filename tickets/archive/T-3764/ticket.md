---
id: T-3764
title: skip win32 os.nice tests in verify test_worker.py
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
- tests/unit/verify/test_worker.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: waive BUG002 confirmatory-only check for win32 platform skip
  actor: logan
  at: '2026-09-04'
  old_length: 214
  new_length: 343
evidence:
- tests/unit/verify/test_worker.py::TestEnsureReducedPriority::test_applies_nice_and_ionice_exactly_once
- tests/unit/verify/test_worker.py::TestEnsureReducedPriority::test_failed_nice_call_never_raises
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI fails TestEnsureReducedPriority.test_applies_nice_and_ionice_exactly_once and test_failed_nice_call_never_raises -- os.nice does not exist on Windows, genuinely POSIX-only. Add skipif(sys.platform==win32).

frob:waive BUG002 reason="win32-only skip; the POSIX-primitive dependency is not reproducible from a Linux parent-commit repro"