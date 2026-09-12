---
id: T-4437
title: Sweep leaked disposable worktrees (bug002 repro, land squash, stale .claude/worktrees
  entries)
state: queued
kind: feature
origin: agent
created: '2026-09-12'
priority: medium
parent: null
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/clean*.py
- src/frob/worktrees/*.py
- tests/unit/test_clean_worktrees*.py
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
MEASURED 2026-09-12: `git worktree list` in this checkout shows 9 leaked `/tmp/frob-bug002-*/wt` worktrees (detached HEAD, locked, oldest from 2026-09-09) and 3 `/tmp/frob-land-squash-*` worktrees (two empty dirs from 2026-09-11 22:15, one from 2026-09-09 with a 19MB cache.db), plus 4 stale entries under .claude/worktrees (t-1906, t-2924, t-3595, t3094-proof-peer all on main with 0 commits ahead, and two non-directories t-2356-scratch-golden-check.py, t1768.patch). The BUG002 repro worktrees and the land squash worktrees are disposable by design and their owners exited (killed lands, killed check runs). Nothing sweeps them: `frob doctor`/`frob clean` do not report them. ACCEPTANCE: (1) a `frob clean --worktrees` (or doctor finding) that lists disposable worktrees whose creator pid is dead and removes them with `git worktree remove --force` + `git worktree prune`; (2) the squash/bug002 creators register their pid in the worktree dir so liveness is decidable; (3) after running it, `git worktree list` here shows none of the 12. F-055 class.
