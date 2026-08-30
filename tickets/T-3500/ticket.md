---
id: T-3500
title: 'macOS-only: /proc-based live-process detection breaks on macOS (bucket C,
  T-3488)'
state: done
kind: bug
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_finish_guard.py;src/frob/tickets/_leases.py;src/frob/tickets/_worktree_guard.py;src/frob/process/_mutate_journal.py
- src/frob/mutate/_journal.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/mutate/_journal.py
  reason: 'T-3500: original ticket named src/frob/process/_mutate_journal.py, a path
    that does not exist -- the real file backing tests/test_mutate_journal.py''s starttime/proc
    logic is src/frob/mutate/_journal.py'
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: append
  reason: 'T-3500: BUG002 waiver -- macOS-only defect cannot fail-then-pass on this
    Linux worktree host'
  actor: logan
  at: '2026-08-30'
  old_length: 1128
  new_length: 1802
evidence:
- tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path
- tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_none_when_no_process_matches
- tests/test_ticket_leases.py::TestRemoveWorktree::test_keeps_a_live_process_worktree
- tests/test_mutate_journal.py::test_recycled_pid_with_mismatched_starttime_is_treated_stale
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while characterizing T-3488's macOS-only CI set (bucket C, 7 tests).

MEASURED (GitHub Actions run 33311990183, macos-latest): 7 tests fail
because the live-process/cwd detection scanner reads /proc directly,
which does not exist on macOS (Linux-only pseudo-filesystem):

- tests/unit/test_land_finish_guard.py (4 tests)
- tests/test_ticket_leases.py::TestRemoveWorktree::test_keeps_a_live_process_worktree
  ('removed' == 'kept:live')
- tests/test_worktree_guard.py (1 test)
- tests/test_mutate_journal.py::test_recycled_pid_with_mismatched_starttime_is_treated_stale
  (0 == 1)

Root cause: whatever helper resolves "is PID N alive, and what is its
start time/cwd" reads /proc/<pid>/{stat,cwd} directly. macOS has no
/proc; the equivalent needs `lsof -p <pid>` (cwd) and `ps -o lstart=`
(start time) or the `psutil`/`os`-level syscalls macOS actually exposes.

Fix shape: either implement a macOS branch (lsof/ps-backed) for the
scanner, or declare a PLATFORM001 boundary (T-2919 doctrine) with tests
asserting the DECLARED direction on macOS -- same pattern T-3076 used
for Windows (docs/design/windows-portability.md).

frob:waive BUG002 reason="T-3500 fixes a macOS-only defect (T-3488 bucket C): the /proc-reading scanner primitives silently degraded to no-finding on any non-Linux platform, including macOS. The designated repro tests genuinely PASS at main on this Linux host, since Linux's /proc code path is unchanged and unbroken -- the new macOS branch (ps/lsof-backed) is unexercised on this host by construction, and can only genuinely fail-then-pass on macos-latest CI, which this implementer cannot dispatch from a Linux worktree. Evidence is confirmatory-only on this host by the nature of the defect, not a weak test -- same shape as T-3488/T-3496/T-3498's own BUG002 waivers."