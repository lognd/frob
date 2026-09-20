---
id: T-4243
title: Fix three Windows land/lease test failures
state: done
kind: bug
origin: human
created: '2026-09-07'
priority: critical
parent: T-4236
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_leases.py
- tests/ticket_land_suite/test_wip.py
- tests/ticket_land_suite/test_land_lock.py
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_leases.py
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: BUG002 confirmatory-only finding is a false positive for Windows-only defects
    the Linux repro-check cannot observe; documented per-defect Windows-before/after
    proof is in the Done report
  actor: logan
  at: '2026-09-07'
  old_length: 239
  new_length: 1085
evidence:
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_dispatches
- tests/ticket_land_suite/test_wip.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
- tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Three Windows-only failures under T-4236 remainder class. 1) reclaim test asserts clean tree, finds land.lock untracked. 2) normalization-only-dirty test asserts dirty, finds clean. 3) reclaim-and-logged test expects a log line, gets none.

frob:waive BUG002 reason="All three defects/premises this ticket fixes are Windows-only (confirmed via winrun against a real Windows interpreter): on this checkouts own platform (Linux), each named evidence test PASSES both before and after the fix, since the Linux run never exercises the platform-specific mechanism (Windows mandatory msvcrt locking vs POSIX advisory fcntl; git clean -fd deleting an open+locked file; Path.write_text newline translation on write). The parent-commit repro-check therefore cannot observe the regression this ticket fixes -- it is blind on this platform by construction, not because the fix is unproven. Each defect was independently reproduced as FAILING on real Windows via winrun before the fix and confirmed PASSING on real Windows via winrun after it; see the Done report for the exact repro transcripts."