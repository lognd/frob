---
id: T-3442
title: 'Five out-of-tree land pipeline tests fail on CI: warm-sweep-stage path, T-1920
  drift guard inert, record-commit probe'
state: queued
kind: bug
origin: agent
created: '2026-08-29'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land.py
- tests/test_ticket_work_and_land_finish.py
- tests/unit/test_land_record_commit.py
- src/frob/tickets/_land.py
- src/frob/tickets/_land_squash.py
- src/frob/tickets/_land_finalize.py
- src/frob/tickets/_archive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33282540898 (ubuntu-latest, HEAD b94cea5d0, 2026-08-30) -- the first run that completed to 100% (20 failures of 12689). This failure is in the cross-platform set (fails on macOS too unless noted). Reproduce locally by node id with -p no:xdist first; if it passes locally, the defect is an environment dependency (git identity, tmp path shape, missing tool, timing) and the fix must make the test hermetic, not skip it.

FIVE land-pipeline tests fail on CI (ubuntu AND macOS):
  tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_true_verdict_lands_normally
      assert PosixPath(.../main/.frob/warm-sweep-stage) == PosixPath(.../main)
  tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard::test_branch_drift_before_final_commit_refuses_by_construction
      land() succeeded despite root drifting off main mid-land -- the T-1920 guard did not fire
  tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_cli_land_invoked_with_root_equal_to_worktree_still_verifies
      SystemExit: 1  (log: tickets: archive refused -- could not measure live git worktrees under <tmp> (git worktree list ...)
  tests/unit/test_land_record_commit.py::TestRecordLandCommitOutOfTree::test_probe_catches_the_in_root_write_positive_control
      the probe saw a CLEAN root across an in-root write+add+commit
  tests/unit/test_land_record_commit.py::TestRecordLandCommitOutOfTree::test_root_never_goes_dirty_while_the_record_is_made
      assert ["M  tickets/...00/ticket.md"] == []
These all touch the out-of-tree land path (warm-sweep-stage, T-1920 drift guard, record-land-commit probe). Two hypotheses to test FIRST: (1) they pass locally and fail in CI because the CI runner git differs (git 2.55 on the runner; no user.name/email; /tmp path shape) -- then make the tests hermetic; (2) they fail locally too -- then the land pipeline regressed on main and the T-1920 guard being inert is a real defect (highest severity of the five). Report which hypothesis held per test.
