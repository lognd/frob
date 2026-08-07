---
id: T-0239
title: graph/gates scan gitignored nested git worktrees -- 73 pct wasted work
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/lang/**
- src/frob/excludes.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_excludes.py::test_is_nested_worktree_detects_own_git_dir
- tests/test_excludes.py::test_is_nested_worktree_git_file_form
- tests/test_excludes.py::test_is_nested_worktree_false_for_root_itself
- tests/test_excludes.py::test_is_nested_worktree_false_for_plain_subdir
- tests/test_excludes.py::test_should_prune_dir_covers_all_three_signals
- tests/test_graph.py::TestExclude::test_nested_git_worktree_pruned_without_config
- tests/test_graph.py::TestExclude::test_walk_source_files_prunes_before_descent
designated_repro_test: null
threat: null
component: null
---
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (HIGH): .claude/worktrees/agent-* checkouts made graph build scan 536 files/3007 symbols vs 144/925 real -- 73 pct of parse/gate work on stale copies; full check 9m47s -> 3m35s after manual exclude. Fix: skip gitignored paths and any directory containing a .git file/dir by DEFAULT (not per-repo config); regression fixture with a nested checkout.