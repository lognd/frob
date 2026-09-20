---
id: T-4246
title: 'Windows land and lease failures: an unreclaimed lock, an inverted dirty check,
  and a reclaim that logs nothing'
state: dropped
kind: bug
origin: agent
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given each of the three tests, when run on Windows and on linux, then both
    pass
  evidence: []
- text: given the linux behaviour of each, when the fix lands, then it is unchanged
  evidence: []
- text: given any case diagnosed as a live defect rather than a test premise, when
    the fix lands, then the defect itself is fixed and covered
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
THREE WINDOWS FAILURES IN THE LAND AND LEASE SUITES, each a question about what
the PLATFORM does rather than what our code says.

    test_ticket_leases.py::TestDispatchLandGuard
      ::test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_dispatches
      asserts a clean tree, finds an untracked lock file left behind

    ticket_land_suite/test_wip.py::TestWipCommitNormalizationOnlyDirty
      ::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
      asserts the tree IS dirty after a normalization-only change, finds it clean

    ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout
      ::test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged
      expects a reclaim log line, gets none

DO NOT ASSUME THESE ARE TEST ARTEFACTS. Two describe behaviour this repository
depends on: an orphaned lock being reclaimed, and a lock file not being left
untracked in the tree. If the reclaim path genuinely does not fire on Windows,
then a killed land there leaves a lock nobody clears -- a live defect in the land
machinery, not a test to relax. And if reclaim fires but logs nothing, that is a
DIFFERENT defect from not firing at all; only running it on Windows separates
them.

The middle one is an inversion worth reading carefully: it expects a dirty tree
and finds a clean one. Line-ending normalization is the obvious suspect, since
that is what the test is about and a Windows checkout normalizes differently. If
normalization simply does not produce a dirty tree there, the test's premise does
not hold on that platform, and the honest fix may be to have the fixture create
the condition explicitly rather than relying on the platform to produce it.

VERIFY ON REAL WINDOWS. A global winrun script syncs this repo to a Windows
mirror and runs natively there -- measured working. Every one of these three is
answerable in a command or two there, and each was previously going to be
answered by reasoning. Run the reclaim directly; ask git directly whether the
normalization dirties the tree.

ONE TRAP: an untracked lock file appearing in a status check is the same shape as
a separate finding about merge temporaries dirtying the shared root. If the fix
is to ignore the lock file, decide whether it should be ignored repo-wide rather
than worked around in one test.

MUST-FIRE FIXTURE:   each of the three passes on Windows and on linux.
MUST-STAY-QUIET:     the linux behaviour of each is unchanged.
THIRD FIXTURE:       for any case diagnosed as a live defect rather than a test
                     premise, the defect itself is fixed and covered.

ACCEPTANCE
- Each of the three classified as a live defect or a platform-invalid premise,
  with the Windows measurement recorded.
- Live defects fixed, not accommodated.
- The ignore-the-lock question decided repo-wide rather than per test.
- All three fixtures committed.

## Drop reason
- 2026-09-07: duplicate of T-4243, which the implementer working these three failures filed first and is already using. I filed this one after checking for existing leaves and finding none -- the agent's filing landed in the gap between my check and my write. Its content adds nothing T-4243 lacks; the classification instruction (live defect versus platform-invalid premise) and the repo-wide ignore-the-lock question are being carried to that agent directly instead
