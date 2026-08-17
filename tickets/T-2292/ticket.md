---
id: T-2292
title: 'reconcile --apply requeued a LIVE ticket mid-land: T-2276 demoted in-progress->queued
  12 minutes after start while its land was running'
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_reconcile.py
- tests/test_ticket_reconcile.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given a ticket whose land process is running, when reconcile --apply runs,
    then that ticket is never requeued regardless of momentary lease state
  evidence: []
- text: given a genuinely stale hold with no process and no worktree, when reconcile
    --apply runs, then it is still requeued (guard not weakened)
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17, real incident on main (see T-2291 for the same
incident's other defect).

`frob ticket reconcile --apply` demoted **T-2276 from `in-progress` to
`queued` while an agent was actively working it and its land was in
flight**. The ticket had started 12 minutes earlier (13:24 start
transition, demotion ~13:3x, land completed 13:45). Its worktree existed,
its agent was live, and its land process was running.

The demotion is committed at 9246d4b5a:

    tickets/T-2276/ticket.md
    -state: in-progress
    +state: queued

The agent had to notice and undo it (2d854269c, "restore T-2276
in-progress state (wrongly reverted to queued while its worktree was
actively landing)") and the wrong state tripped a TerminalStateRegression
guard during its land.

MECHANISM (hypothesis, implementer to confirm): reconcile classifies a
stale hold as `IN_PROGRESS` with no live lease. During a land, the lease
is transiently absent or reclaimed -- the human-authored recovery commit
message at the time literally reads "after orphaned lock reclaim". So
reconcile races the land: it samples the lease exactly in the window where
the land holds it differently, concludes the hold is abandoned, and
requeues a ticket that is more active than any other ticket in the repo.

WHY THIS IS THE DANGEROUS DIRECTION: the staleness predicate's false
NEGATIVE (missing a genuinely stale hold) costs one leaked lease, found by
the next reconcile. Its false POSITIVE demotes live work, corrupts the
ledger under a running land, and is caught only if an agent happens to
notice. These are not symmetric, so the predicate must be biased toward
leaving holds alone.

FIX DIRECTION: never requeue a ticket that has a live land process or a
live worktree, independent of what the lease file says at the sampled
instant -- reconcile already performs a land-process scan (T-1619) for its
own refusal, so the signal is in hand. Consider also requiring a minimum
hold age; a 12-minute-old in-progress ticket is not a stale hold by any
reasonable definition.

POSITIVE CONTROL REQUIRED: (1) must-still-pass -- a genuinely stale hold
(dead agent, no process, no worktree, old) is still requeued; (2)
must-now-fail -- a hold with a running land is NEVER requeued, asserted
while the land is actually in flight rather than simulated by deleting a
lease file.
