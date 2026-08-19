---
id: T-2651
title: fleet_status enumerates leases from worktrees, so a leaked lease with no worktree
  is invisible -- the exact case that matters
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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

While T-2377 was `state: in-progress` with `docs/modules/gates.md` in its
declared scope, `scripts/fleet_status.py` reported:

    LEASES 4 (3 live)
      T-1686 -> frob  [root-resident]
      T-2581 -> m5-m6-series  [live]
      T-2626 -> t2615-t2626  [live]
      T-2638 -> t2629-t2638  [live]

T-2377 is absent. Yet `frob ticket start T-2613` refused with a real
collision: *"T-2613's declared scope collides with in-progress T-2377's
lease on 'docs/modules/gates.md'"*. The start-time check is authoritative
and saw the lease; the status tool did not.

## Root cause hypothesis -- verify before fixing

Every lease `fleet_status` DID list maps to an existing worktree
(`m5-m6-series`, `t2615-t2626`, `t2629-t2638`, plus the root-resident one).
T-2377 had NO worktree -- confirmed, `git worktree list | grep -c t-2377`
returned 0.

So the reporter appears to enumerate WORKTREES and attribute a lease to
each, rather than enumerating in-progress TICKETS and reading their
declared scope. That inverts the relationship: a lease is a property of an
in-progress ticket's scope (T-0453), and a worktree is merely where the
work usually happens.

## Why this is the worst possible blind spot

The leases that need surfacing most are exactly the ones this misses. A
healthy lease belongs to an agent actively working in a worktree, and it
releases when that work lands. A LEAKED lease belongs to a ticket that is
in-progress with nobody working it -- typically because its worktree was
removed or it was blocked and never requeued. That is precisely the
no-worktree case the reporter cannot see.

Measured cost of this instance: T-2377 was BLOCKED nine hours ago (blocked
by T-2568, still queued), its worktree removed, and it was left
`in-progress`. For those nine hours it held a write lease on
`docs/modules/gates.md` that it could not possibly use. That blocked T-2613
outright and forced at least four separate tickets (T-2569, T-2576, T-2579,
T-2588) to skip Tier-A doc fixes with "under T-2377's live lease" as the
reason -- several of which then needed their own follow-up tickets.

I resolved this instance by requeueing T-2377. The reporting gap is what
this ticket fixes.

## Fix

Enumerate leases from in-progress TICKETS and their declared scope, then
annotate each with its worktree if one exists. Report a lease whose ticket
is in-progress with NO live worktree distinctly -- that is the leak
signature and it should be loud, not absent.

Consider also flagging the specific shape found here: a ticket that is
BLOCKED (open `blocked_by`) yet still `in-progress`. It cannot proceed, so
any lease it holds is pure waste. That may deserve its own check; file
separately if it does not fit cleanly.

## Do NOT

- Do NOT fix this by having the status tool call the start-time collision
  check per ticket pair. That is O(n^2) and this tool runs constantly.
  Read the ticket state and scope directly, which is what the lease IS.
- Do NOT drop the worktree annotation. Knowing WHERE a lease is being
  worked is useful; the bug is that worktree presence is currently the
  trigger rather than a detail.

## Positive controls, both directions

- an in-progress ticket with a declared scope and NO worktree appears in
  the lease list, flagged as a probable leak. This is the case that was
  missing and it is the one that proves the fix
- an in-progress ticket with a live worktree still appears exactly as
  today, with its worktree named
- a QUEUED ticket with a declared scope does NOT appear -- leases bind only
  at in-progress (T-0453), and reporting queued scopes as leases would make
  the list useless in the opposite direction
- the reported set matches what `frob ticket start` would actually refuse
  on, for a sample of tickets
