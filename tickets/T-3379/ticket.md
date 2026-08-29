---
id: T-3379
title: Rapid-sweep self-absorb (record-as-debt) path is blocked by the worktree-guard
  it always runs under
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/**
- src/frob/tickets/_worktree_guard.py
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
Observed during T-2667's land (2026-08-29, under fleet load): the rapid
sweep's self-absorb path -- the mechanism that records a new finding as
rapid-debt instead of filing a ticket when a sweep runs under an agent
with a leased worktree -- itself refused to run because of the very
lease that is its ONLY operating context:

  ERROR: worktree-guard: agent leased to
  /home/logan/projects/frob/.claude/worktrees/t-2667; refusing to
  mutate /home/logan/projects/frob (cwd resolved to
  /home/logan/projects/frob) -- cd into the leased worktree, or clear
  FROB_WORKTREE if this is deliberate
  ERROR: rapid sweep: T-3361 introduced 1 new error(s) but the
  regression ticket could NOT be filed (WorktreeLeaseViolation:
  FROB_WORKTREE is leased to a different worktree than this command's
  cwd) -- pairs: [('TICK002', 'tickets.md')]

This happened twice in the same land session (visible at both
06:52-ish and again a few minutes later, both against the TICK002 @
tickets.md finding at batch a5b80af0e8b8919eb712b2e437f32a5567a438eb).

The escape valve (recording a sweep finding as accepted rapid-debt
without filing a full ticket) exists specifically for exactly this
situation -- a background rapid-sweep triggered from inside a leased
agent worktree during a `frob ticket land`. But the worktree-guard
that blocks writes to the shared root (T-2850, correctly protecting
against an agent accidentally editing the primary checkout) does not
distinguish "the rapid-sweep subsystem legitimately needs to record a
debt entry against the ROOT's rapid-debt.jsonl" from "an agent is
trying to hand-edit files in the root it should not touch". So the
valve is inert in the one context it is designed to fire in: it always
runs from inside a leased agent's land, never from an unleased shell.

When this path fails, the finding is left unabsorbed (watermark not
advanced, per the log: "1 new finding(s) ... could NOT be filed --
watermark NOT advanced ... baseline left UNCHANGED") and reappears as
NEW on the next verify-worker wake -- which, combined with T-3378's
TICK002 self-deadlock, means findings that should have been quietly
absorbed as rapid debt instead keep re-triggering quarantine checks
fleet-wide.

Candidate fix (not decided here): the rapid-sweep's debt-recording
write path needs its own exemption from the worktree-guard (similar to
how tickets.md/tickets/** already carry a blanket exemption, T-2850),
scoped narrowly to rapid-debt.jsonl writes originating from the sweep
subsystem itself, not a general loosening of the guard.
