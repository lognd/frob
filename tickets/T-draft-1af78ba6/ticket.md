---
id: T-draft-1af78ba6
title: SUPPRESS001 ty diagnostic correlation doubles the worktree path (root/.claude/worktrees/x/.claude/worktrees/x/...)
  and cannot read any file
state: queued
kind: bug
origin: agent
created: '2026-09-15'
priority: medium
parent: null
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: v0.532.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_suppress.py
- tests/unit/test_suppress_worktree_path.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN frob check runs against a worktree under <root>/.claude/worktrees/<x>
    WHEN SUPPRESS001 correlates ty diagnostics THEN it resolves each diagnostic path
    once, relative to the worktree, and reads the file
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-15 in the land log of T-draft-926571db: dozens of 'SUPPRESS001: could not read .claude/worktrees/t-draft-926571db/tests/... for ty diagnostic correlation: [Errno 2] .../frob/.claude/worktrees/t-draft-926571db/.claude/worktrees/t-draft-926571db/tests/...'. ty reports paths relative to the repo root while the correlation joins them onto the worktree path again. Every ty diagnostic in a worktree check is therefore uncorrelated: a silent zero for SUPPRESS001 inside worktrees. Find the real file first with git grep SUPPRESS001 -- src/frob/gates; adjust scope if it is not _suppress.py.