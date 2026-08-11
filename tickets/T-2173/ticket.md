---
id: T-2173
title: 'T-1720''s post-land auto-rebase conflicts on ledger files every time and leaves
  worktrees stale: 4 occurrences today across 3 worktrees, and git merge succeeds
  where rebase fails'
state: done
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
- tests/unit/test_land_auto_rebase.py
- docs/modules/tickets.md
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
- op: add
  glob: tests/unit/test_land_auto_rebase.py
  reason: 'Renaming _auto_rebase_worktree_onto_main to _auto_sync_worktree_onto_main

    (rebase -> merge, T-2173) breaks two existing references outside

    _land_cmd.py: the existing unit test file that imports the old name

    directly, and one frob:describes doc anchor comment naming the old

    symbol. Both need updating in the same change or they break/go stale.

    '
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/modules/tickets.md
  reason: 'Renaming _auto_rebase_worktree_onto_main to _auto_sync_worktree_onto_main

    (rebase -> merge, T-2173) breaks two existing references outside

    _land_cmd.py: the existing unit test file that imports the old name

    directly, and one frob:describes doc anchor comment naming the old

    symbol. Both need updating in the same change or they break/go stale.

    '
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_merges_the_worktree_onto_the_new_main_tip
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_squash_then_rebase_conflicts_but_merge_does_not
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_a_real_conflict_aborts_cleanly_and_does_not_fail_the_land
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_dirty_worktree_is_skipped_rather_than_merged_into
designated_repro_test: tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_squash_then_rebase_conflicts_but_merge_does_not
threat: null
component: null
anchor: false
anchor_reason: null
---
