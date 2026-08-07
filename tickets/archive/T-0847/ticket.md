---
id: T-0847
title: 'land: wip pre-land snapshot fails on line-ending phantom-dirty worktrees (nothing
  to commit after add -A renormalizes)'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
designated_repro_test: null
threat: null
component: null
---
Seen twice landing T-0608 and T-0605 (2026-07-23): _porcelain_dirty reports a worktree dirty because git status --porcelain lists files whose only difference is CRLF/LF normalization (WSL autocrlf phantom-modified). _wip_commit then runs git add -A, which renormalizes to the identical blob, and the commit exits 1 'nothing to commit' with no stderr -> land aborts GitFailed. The failed attempt's add -A clears the phantom, so a blind retry succeeds -- a confusing two-attempt ritual. Fix: after add -A, re-check staged state (git diff --cached --quiet) and treat an empty stage as 'nothing to snapshot, proceed' instead of a failed land; test with a fixture repo exhibiting a normalization-only status line.