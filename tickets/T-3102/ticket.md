---
id: T-3102
title: Fold the pre-commit sweep into land's out-of-tree composed commit
state: queued
kind: feature
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land_release.py
- src/frob/tickets/_land_squash.py
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
T-3095 (isolate land's post-squash file-mutating stages so the whole
transaction is invisible in the shared tree) identified the pre-commit-
sweep sub-stage (_apply_pre_commit_sweep_or_unwind, src/frob/tickets/
_land_squash.py) as the genuinely hard one of the three: Tier-A auto-fix
MUTATES content, so whatever it produces must end up in the composed
tree the land eventually publishes, not in a working tree nobody keeps.

WANTED: apply the SAME disposable-`git worktree` technique T-3095
introduced for the release bump (`_apply_release_bump_out_of_tree`,
src/frob/tickets/_land_release.py) to the pre-commit sweep: run `frob
check`/ruff/Tier-A auto-fix against the disposable worktree (chained
after the release-bump step, on the SAME worktree, before it is folded
into a commit), so any auto-fix content lands in the composed commit
object rather than a working tree that is thrown away. This is the step
that finally makes root's `git status --porcelain` read clean for the
land's ENTIRE post-squash span, not just the release-bump slice.

Depends on T-3089's re-scoped wiring existing first (there needs to be a
single disposable worktree the release bump AND the sweep both run
against, in sequence, before one fold-and-publish).
