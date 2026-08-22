---
id: T-2886
title: 'Fleet worktrees run stale src/ post-land: audit staleness/leases/unlanded
  work, propose per-worktree disposition'
state: queued
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/worktrees/
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
## Description

Measured tonight (coordinator + confirmed independently): each git
worktree under .claude/worktrees/ carries its OWN editable install
pointing at THAT worktree's src/, not main's. On the primary checkout,
9 worktrees have arm_parent_death_signal in their own
src/frob/process/_reap.py (T-2849's forkserver-leak fix); the rest do
not. Any agent running frob check from a stale worktree executes
pre-T-2849 pool-construction code and leaks forkservers exactly as
before the fix.

THE GENERAL FORM (the real finding, not just this one leak): a stale
worktree runs stale code for EVERY land, not just T-2849's. Any fix
whose correctness depends on all agents actually running it is silently
defeated by a worktree that never merged main. This is a fleet-
integrity problem.

## Plan

1. Enumerate every worktree under .claude/worktrees/, measure staleness
   (commits behind main, last-commit age via fleet_status).
2. For each, check for a live lease (in-progress ticket) -- active, not
   stale.
3. For each remaining candidate, verify by CONTENT not ancestry before
   proposing removal: `git -C <wt> log --oneline main..HEAD` plus
   `git diff --stat main <branch> -- src tests docs`. Empty content
   diff = genuinely superseded. Non-empty = someone's unlanded work;
   do not touch.
4. Propose a disposition per worktree: refresh (merge main), reap
   (coordinator-approved removal only), or leave (live lease / genuine
   unlanded work needing hand-off).
5. Do NOT bulk-remove anything. Report findings; removals need explicit
   coordinator approval.
6. Record a recommendation on whether `frob ticket work` should refuse
   or auto-refresh a worktree whose branch is more than N commits
   behind main -- this ticket documents the recommendation, a follow-up
   ticket would build it.

## Failure log

(none yet)