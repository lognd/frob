---
id: T-5162
title: pre-commit land-owned guard diffs CHANGELOG.md and changelog.d against literal
  main, so every dev merge inside a worktree is refused while main is frozen
state: queued
kind: bug
origin: human
created: '2026-09-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/doctor_runner.py
- .claude/hooks/*.py
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
Measured 2026-09-20: .git/hooks/pre-commit _t1742_staged_diverges_from_main runs 'git diff --cached --quiet main -- CHANGELOG.md' (T-0731) and the same for changelog.d/T-####.md (T-2445). With main frozen at 0.531.0 and dev the land target, merging dev into any worktree stages those files as divergent from main and the merge commit is refused; excluding them from the merge makes the branch delete them relative to dev and land refuses with UnownedDeletions. The coordinator runner now commits the sync under FROB_LAND_INTERNAL=1, the documented cover, but a plain dev sync should not need it. Fix: the guard compares against the land target branch (same source as LandReport.target_branch and T-1273's check base), and the installed hook is regenerated from the template. Found while coordinating lands.