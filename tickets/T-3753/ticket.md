---
id: T-3753
title: 'win32 test portability (fork/sysconf class): skipif POSIX fork-context and
  os.sysconf tests'
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
scope_changes:
- op: add
  glob: tests/test_coverage.py
  reason: only file in the fork/sysconf class actually needing a skipif; the other
    9 assigned files already inline-guard their real os.fork/get_context(fork)/os.sysconf
    usages
  actor: logan
  at: '2026-09-04'
body_changes:
- mode: set
  reason: audit findings + waiver reason for the win32 fork/sysconf class
  actor: logan
  at: '2026-09-04'
  old_length: 0
  new_length: 2035
evidence:
- tests/test_coverage.py::TestSpawnWithWatchdog::test_killed_process_group_leaves_no_surviving_children
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

Part of T-3076 win32 test-portability drain. Assigned files (the
os.fork/fork-context/os.sysconf class):

  tests/gates_suite/test_run.py
  tests/test_coverage.py
  tests/test_vet_capability.py
  tests/ticket_land_suite/test_ledger_splice.py
  tests/ticket_land_suite/test_verify_reset.py
  tests/unit/arch_suite/test_concurrency.py
  tests/unit/test_fix_engine_journal.py
  tests/unit/test_land_finish_guard.py
  tests/unit/test_land_lock_liveness.py
  tests/unit/test_process_reap.py

Audit result: of these 10 files, 9 already handle win32 correctly (either
they never actually execute os.fork/a fork mp-context/os.sysconf -- e.g.
static-analysis fixtures and docstring/comment prose in
test_vet_capability.py and test_concurrency.py, or a "spawn" context in
test_ledger_splice.py, or a portable ternary in test_fix_engine_journal.py,
or dynamic method selection in test_run.py -- or they already carry an
inline `if sys.platform == "win32": pytest.skip(...)` guard around the
one call site that needs it: test_verify_reset.py (4 tests),
test_land_finish_guard.py (1 test), test_land_lock_liveness.py (1 shared
helper covering 2 tests), and test_process_reap.py's
test_arms_successfully_on_linux (guarded by its own
`sys.platform != "linux"` skip, a superset of win32) and its os.sysconf
tests (already monkeypatched via `raising=False`, portable by
construction).

The one genuine gap: tests/test_coverage.py::TestSpawnWithWatchdog::
test_killed_process_group_leaves_no_surviving_children spawns a real
subprocess script containing `os.fork()` with no guard at all.

## Plan

Add a `@pytest.mark.skipif(sys.platform == "win32", reason=...)` decorator
to that one test. Scope narrowed to tests/test_coverage.py only -- the
other 9 files need no edits.

frob:waive BUG002 reason="Windows-only defect: os.fork / the 'fork' mp context / os.sysconf are absent on win32 so these tests cannot run there; on the Linux land host they pass at parent and fix alike (no repro); skipif converts the win32 error to a clean skip"
