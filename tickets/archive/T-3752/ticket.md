---
id: T-3752
title: 'win32 test portability (fcntl class): skipif POSIX fcntl-locking tests'
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
- tests/unit/rapid_sweep_suite/test_baseline.py
- tests/unit/test_process_lock.py
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/rapid_sweep_suite/test_baseline.py
  reason: 'win32 portability: skipif tests that unconditionally import the POSIX-only
    fcntl module'
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/unit/test_process_lock.py
  reason: 'win32 portability: skipif tests that unconditionally import the POSIX-only
    fcntl module'
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: 'win32 portability: skipif tests that unconditionally import the POSIX-only
    fcntl module'
  actor: logan
  at: '2026-09-04'
body_changes:
- mode: set
  reason: describe scope, findings, and BUG002 waiver
  actor: logan
  at: '2026-09-04'
  old_length: 0
  new_length: 1827
evidence:
- tests/unit/rapid_sweep_suite/test_baseline.py::TestBaselineLock::test_serializes_two_concurrent_holders
- tests/unit/test_process_lock.py::TestPortableFlock::test_windows_branch_selected_when_fcntl_absent
- tests/unit/test_process_lock.py::TestDerivedStateLockPlatformBackends::test_windows_backend_round_trips
- tests/unit/test_ticket_store.py::TestLedgerLockPlatformBackends::test_windows_backend_round_trips
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

Windows-only defect: three test modules in the fcntl class each contain
one or more tests that unconditionally `import fcntl` (or `import fcntl
as _real_fcntl`) at the start of the test body, or bury the win32 skip
check inside a nested fake-msvcrt callback that only runs AFTER the
unconditional import already raised. On win32 these tests fail with
`ModuleNotFoundError: No module named 'fcntl'` before any skip logic can
run. This ticket adds a `@pytest.mark.skipif(sys.platform == "win32", ...)`
decorator directly on each affected test so the import is never reached
on Windows.

Two other files initially suspected of being in the fcntl class
(tests/test_narrative_blocks.py, tests/test_walk_lint_gate.py) were
checked and found to reference "fcntl" only inside string/AST fixtures
fed to a linter under test -- they never actually import or call fcntl,
so they were left untouched (out of scope, no change needed). Likewise
tests/test_ticket_reconcile.py, tests/test_tickets_parent.py,
tests/test_tickets_priority.py, tests/test_ticket_leases.py, and
tests/ticket_land_suite/test_land_lock.py were checked and found to
already guard every fcntl-using test with an inline
`if sys.platform == "win32": pytest.skip(...)` placed BEFORE the
`import fcntl` line -- already portable, so left untouched.

## Plan

- Add skipif decorators to the 5 unconditionally-fcntl-importing tests
  found in tests/unit/rapid_sweep_suite/test_baseline.py,
  tests/unit/test_process_lock.py (x3), and tests/unit/test_ticket_store.py.
- Verify green on Linux (skipif only fires on win32).

frob:waive BUG002 reason="Windows-only defect: fcntl is absent on win32 so these tests cannot run there; on the Linux land host they pass at parent and fix alike (no repro); skipif converts the win32 ModuleNotFoundError to a clean skip"