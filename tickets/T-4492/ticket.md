---
id: T-4492
title: 'ticket work and worktree sweep hardcode main: worktrees branch from and merge
  main instead of the land target (dev)'
state: done
kind: bug
origin: agent
created: '2026-09-15'
priority: critical
parent: T-4410
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_lifecycle.py
- src/frob/tickets/_worktree_sweep.py
- tests/unit/test_lifecycle_work_base.py
- src/frob/tickets/_land.py
- tests/unit/test_land_leaked_tickets_lease_hoist.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: shared branch-resolution helper for work/sweep must live next to T-3787's
    _resolve_land_target_branch to avoid duplicating the current-branch/config/main
    fallback logic
  actor: logan
  at: '2026-09-15'
- op: add
  glob: tests/unit/test_land_leaked_tickets_lease_hoist.py
  reason: 'T-4492 second defect (coordinator directive): unit test for the read_all_leases
    hoist in _find_leaked_tickets'
  actor: logan
  at: '2026-09-15'
evidence:
- tests/unit/test_lifecycle_work_base.py::TestWorkBranchesFromRootsCurrentBranch::test_worktree_head_contains_devs_own_tip_commit
- tests/unit/test_lifecycle_work_base.py::TestWorktreeSweepCountsAgainstResolvedTarget::test_counts_commits_ahead_of_dev_not_ahead_of_main
- tests/unit/test_lifecycle_work_base.py::TestWorkBranchesFromRootsCurrentBranch::test_byte_for_byte_historical_when_root_is_on_main_no_config
- tests/unit/test_land_leaked_tickets_lease_hoist.py::TestFindLeakedTicketsHoistsReadAllLeases::test_read_all_leases_called_at_most_once_across_many_candidates
designated_repro_test: tests/unit/test_lifecycle_work_base.py::TestWorkBranchesFromRootsCurrentBranch::test_worktree_head_contains_devs_own_tip_commit
acceptance:
- text: GIVEN the root checkout on branch dev with ticket_land_branch = dev WHEN frob
    ticket work creates a worktree THEN the worktree branches from dev, not main,
    and its freshness merge merges dev
  evidence:
  - tests/unit/test_lifecycle_work_base.py::TestWorkBranchesFromRootsCurrentBranch::test_worktree_head_contains_devs_own_tip_commit
- text: GIVEN a worktree branch and the land target dev WHEN the worktree sweep counts
    unlanded commits THEN it counts dev..branch, not main..branch
  evidence:
  - tests/unit/test_lifecycle_work_base.py::TestWorktreeSweepCountsAgainstResolvedTarget::test_counts_commits_ahead_of_dev_not_ahead_of_main
- text: GIVEN no ticket_land_branch config and root on main WHEN work and sweep run
    THEN behavior is byte-for-byte the historical main behavior
  evidence:
  - tests/unit/test_lifecycle_work_base.py::TestWorkBranchesFromRootsCurrentBranch::test_byte_for_byte_historical_when_root_is_on_main_no_config
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-15 right after switching the root to dev: frob ticket work T-4496 created its worktree from main (b10d67a0f) although the root was on dev one commit ahead (c58d4d423, the ticket's own filing commit), so frob ticket start inside the worktree failed with 'no ticket'. Sites: src/frob/app/ticket_runner/_lifecycle.py (worktree add -b <branch> main; git merge main in _ensure_worktree_fresh) and src/frob/tickets/_worktree_sweep.py (rev-list --count main..branch, three-dot main...branch diff). T-3787 made land itself branch-aware via ticket_land_branch / root's current branch; work and sweep must resolve the same target through one shared helper (root's current branch, falling back to ticket_land_branch, then main), never a literal.