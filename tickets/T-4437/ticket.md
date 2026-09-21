---
id: T-4437
title: Sweep leaked disposable worktrees (bug002 repro, land squash, stale .claude/worktrees
  entries)
state: in-progress
kind: feature
origin: agent
created: '2026-09-12'
priority: medium
parent: null
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/clean*.py
- src/frob/worktrees/*.py
- tests/unit/test_clean_worktrees*.py
- src/frob/_cli_parsers/_misc.py
- src/frob/gates/_bug_repro.py
- src/frob/tickets/_land_compose.py
- docs/modules/clean.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: wire the --sweep-disposable-worktrees flag onto frob clean and stamp creator
    pid at the two disposable-worktree creation sites this tickets own acceptance
    criteria 1/2 name
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/gates/_bug_repro.py
  reason: wire the --sweep-disposable-worktrees flag onto frob clean and stamp creator
    pid at the two disposable-worktree creation sites this tickets own acceptance
    criteria 1/2 name
  actor: logan
  at: '2026-09-20'
- op: add
  glob: src/frob/tickets/_land_compose.py
  reason: wire the --sweep-disposable-worktrees flag onto frob clean and stamp creator
    pid at the two disposable-worktree creation sites this tickets own acceptance
    criteria 1/2 name
  actor: logan
  at: '2026-09-20'
- op: add
  glob: docs/modules/clean.md
  reason: document --sweep-disposable-worktrees and the new frob.worktrees public
    symbols this tickets own land refused for missing frob:doc
  actor: logan
  at: '2026-09-20'
triage_changes:
- field: sprint
  old_value: v0.532.0
  new_value: backlog
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-15'
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-15'
- field: sprint
  old_value: backlog
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.535.0
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: milestone
  old_value: 1.0.0
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: set
  reason: 'DOC006: the body named a not-yet-existing CLI invocation (frob clean --worktrees),
    which failed tests/test_docptr_gate.py on ubuntu and macOS in CI run 34675057655'
  actor: logan
  at: '2026-09-12'
  old_length: 1054
  new_length: 1072
evidence:
- tests/unit/test_clean_worktrees_sweep.py::TestSweepDisposableWorktrees::test_dead_stamped_worktree_is_removed
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-12: `git worktree list` in this checkout shows 9 leaked `/tmp/frob-bug002-*/wt` worktrees (detached HEAD, locked, oldest from 2026-09-09) and 3 `/tmp/frob-land-squash-*` worktrees (two empty dirs from 2026-09-11 22:15, one from 2026-09-09 with a 19MB cache.db), plus 4 stale entries under .claude/worktrees (t-1906, t-2924, t-3595, t3094-proof-peer all on main with 0 commits ahead, and two non-directories t-2356-scratch-golden-check.py, t1768.patch). The BUG002 repro worktrees and the land squash worktrees are disposable by design and their owners exited (killed lands, killed check runs). Nothing sweeps them: `frob doctor`/`frob clean` do not report them. ACCEPTANCE: (1) a clean-subcommand flag (name to be decided) or a doctor finding that lists disposable worktrees whose creator pid is dead and removes them with `git worktree remove --force` + `git worktree prune`; (2) the squash/bug002 creators register their pid in the worktree dir so liveness is decidable; (3) after running it, `git worktree list` here shows none of the 12. F-055 class.