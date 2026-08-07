---
id: T-0790
title: 'land: CloseFailed-retry path rebuilds worktree branch onto main and completeness
  guard compares branch against itself'
state: dropped
kind: bug
origin: agent
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a land that failed post-merge with CloseFailed and was retried after
    a ledger fix in the worktree WHEN land runs again THEN it either completes the
    squash-apply of the real diff or refuses with an accurate reason; the T-0761 guard
    must compare the worktree branch against the ROOT's HEAD, never against the branch
    itself; a regression test reproduces the retry-after-CloseFailed shape
  evidence: []
threat: null
component: null
---
Observed landing T-0676 (2026-07-23): first land failed post-merge with EvidenceScopeUnbound (the T-0774 residual); after a scope-add fix in the worktree, the retry committed a wip pre-land snapshot REBUILT onto main's tip (dropping the original commit lineage 677b8a7f/f586d2a8/a506e4f6 from the branch history), merged main, finalized+closed -- then the T-0761 completeness guard errored claiming HEAD has no commits beyond the true merge-base with <its own branch name>, i.e. merge-base(HEAD, HEAD)==HEAD, a tautology. The genuine diff vs main (2 doc files + ledger) existed and was recovered by manual squash-apply (commit on main). Root-cause the retry path's branch/ref bookkeeping and fix the guard's comparison ref.

## Drop reason
- 2026-07-23: misdiagnosis: the tautological comparison occurred because the operator ran frob ticket land with cwd INSIDE the worktree (root defaulted to the worktree, making root==worktree) -- the T-0761 guard fired correctly. The real defects are captured in the replacement retry-robustness ticket