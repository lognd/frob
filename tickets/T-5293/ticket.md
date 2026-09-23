---
id: T-5293
title: test_release.py changelog-fragment-ownership check fails on dev tip
state: dropped
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_release.py
- src/frob/release
- changelog.d/T-4759.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: changelog.d/T-4759.md
  reason: the actual fix is deleting the stray fragment
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
evidence:
- tests/test_release.py::TestNoStrayFragmentForNonDoneTicket::test_every_changelog_fragment_belongs_to_a_done_ticket
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5293
branch: t-5293
---
gh run 35717833933; re-verified on dev tip 3acf8c6b30: tests/test_release.py::TestNoStrayFragmentForNonDoneTicket::test_every_changelog_fragment_belongs_to_a_done_ticket fails standalone (not a fleet version-bump race -- reproduced serially, single test, clean checkout).

## Failure log
- 2026-09-23 attempt 1: TICK015: dead worktree (no live process holds worktree /home/logan/projects/frob/.claude/worktrees/t-5293), requeued by frob check

## Drop reason
- 2026-09-23: landed by content: changelog.d/T-4759.md is gone on dev via a sibling's --allow-cross-ticket land; its own land record was reset by TICK015 (T-5358) and re-landing an empty diff refuses