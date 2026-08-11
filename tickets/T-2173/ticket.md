---
id: T-2173
title: 'T-1720''s post-land auto-rebase conflicts on ledger files every time and leaves
  worktrees stale: 4 occurrences today across 3 worktrees, and git merge succeeds
  where rebase fails'
state: queued
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'Coordinator scope error, corrected on the agent''s evidence: the auto-rebase
    lives in _land_cmd.py::_auto_rebase_worktree_onto_main (T-1720, line 1942; the
    ''auto-rebase onto %s failed or conflicted'' log is at 2005). _land_git_ops.py
    contains ZERO rebase code (git grep -c rebase = 0) -- it is the git-plumbing/wip-commit
    family. I guessed the file rather than grepping for the log line.'
  actor: logan
  at: '2026-08-11'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'Coordinator scope error, corrected on the agent''s evidence: the auto-rebase
    lives in _land_cmd.py::_auto_rebase_worktree_onto_main (T-1720, line 1942; the
    ''auto-rebase onto %s failed or conflicted'' log is at 2005). _land_git_ops.py
    contains ZERO rebase code (git grep -c rebase = 0) -- it is the git-plumbing/wip-commit
    family. I guessed the file rather than grepping for the log line.'
  actor: logan
  at: '2026-08-11'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
