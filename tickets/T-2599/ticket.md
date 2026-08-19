---
id: T-2599
title: '34 registered worktrees, ~20 idle 9-13 days: audit needs a stranded-vs-stale
  test that squash-landing does not fool'
state: queued
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- scripts/fleet_status.py
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
## Measured

34 registered git worktrees under `.claude/worktrees/`. Roughly 20 have not
been committed to in 9-13 days (`dev-friction`, `gate-internals`,
`land-integrity-series`, `reg-enforce`, `rule-bookkeeping`, `t-2071`,
`t-2125`, `t-2355`, `t-2356`, `t1860-series`, `t1893-t1908`, and others).
Git additionally warns during ordinary commits:

    warning: There are too many unreachable loose objects;
    run 'git prune' to remove them.

Each worktree holds a full checkout plus its own index. This costs disk,
slows every `git worktree list`-based tool, and makes the real question --
"is anyone still working this?" -- expensive to answer.

## DO NOT bulk-remove these. The obvious tests are all WRONG.

This is the dangerous part and the reason this is a ticket rather than a
one-line cleanup. A clean-but-unlanded branch is invisible to the queue and
is exactly what a naive sweep marks removable. Three plausible tests were
tried and all three give the wrong answer:

1. `git log main..HEAD` (unlanded commit count) -- OVERCOUNTS badly. `frob
   ticket land` SQUASHES, so a worktree whose content fully landed still
   shows all its pre-squash originals as "unlanded". Measured: 23 of 23
   worktrees looked like they held unlanded work.
2. `git diff --stat main..HEAD` -- CONFLATES ahead with behind. A worktree
   that is merely STALE shows enormous deltas: `gate-internals` reported
   "534 files changed, 12649 insertions, 107063 deletions", which is main
   having moved on, not stranded work.
3. Reading the insertion count alone -- still wrong without checking
   DIRECTION. `t-2588` showed "1 insertion not on main"; inspecting it,
   the line was an OLD one-line docstring that main had deliberately
   REPLACED with a longer one. The worktree was behind, not ahead.

## The test that actually works

For each worktree, diff against main restricted to source paths and read
the `+` side WITH its context, confirming whether main has an equivalent:

    git -C <wt> diff main HEAD -- src tests docs scripts

Content that exists only in the worktree and has no counterpart on main is
genuinely stranded. Everything else is stale and safe. Verify the ticket's
own state is terminal AND its land commit is an ancestor of main before
removing, and never trust a single number without looking at the hunk.

Two worktrees were removed by hand this way (`t-2584`, `t-2588`), both
confirmed behind-main with zero stranded content.

## Fix

Add an audit command that classifies every registered worktree as
STRANDED / STALE / ACTIVE using the test above, and REPORTS -- it must not
delete anything by default. Removal stays a separate explicit action taken
per-worktree after reading the report.

Prefer surfacing the STRANDED count where the operator already looks
(`scripts/fleet_status.py` already reports worktrees and their idle age)
over adding a command someone has to know to run.

Also worth handling: the unreachable-loose-object growth. `git prune` is
NOT safe to run blindly while worktrees hold references; determine the
correct incantation and whether it needs the worktrees pruned first.

## Positive controls, both directions

- a worktree holding source content absent from main is classified
  STRANDED and is NOT proposed for removal
- a worktree whose content fully landed via squash is classified STALE
  despite showing many `main..HEAD` commits -- this is test 1's failure and
  the single most important case
- a worktree merely behind main (large deletion-side diff) is STALE, not
  STRANDED -- test 2's failure
- an ACTIVE worktree belonging to a non-terminal ticket is never proposed
  for removal regardless of its diff
