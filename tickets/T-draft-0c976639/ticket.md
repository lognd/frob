---
id: T-draft-0c976639
title: 'ticket work and worktree sweep hardcode main: worktrees branch from and merge
  main instead of the land target (dev)'
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN the root checkout on branch dev with ticket_land_branch = dev WHEN frob
    ticket work creates a worktree THEN the worktree branches from dev, not main,
    and its freshness merge merges dev
  evidence: []
- text: GIVEN a worktree branch and the land target dev WHEN the worktree sweep counts
    unlanded commits THEN it counts dev..branch, not main..branch
  evidence: []
- text: GIVEN no ticket_land_branch config and root on main WHEN work and sweep run
    THEN behavior is byte-for-byte the historical main behavior
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-15 right after switching the root to dev: frob ticket work T-draft-926571db created its worktree from main (b10d67a0f) although the root was on dev one commit ahead (c58d4d423, the ticket's own filing commit), so frob ticket start inside the worktree failed with 'no ticket'. Sites: src/frob/app/ticket_runner/_lifecycle.py (worktree add -b <branch> main; git merge main in _ensure_worktree_fresh) and src/frob/tickets/_worktree_sweep.py (rev-list --count main..branch, three-dot main...branch diff). T-3787 made land itself branch-aware via ticket_land_branch / root's current branch; work and sweep must resolve the same target through one shared helper (root's current branch, falling back to ticket_land_branch, then main), never a literal.