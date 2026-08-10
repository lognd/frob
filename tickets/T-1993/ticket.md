---
id: T-1993
title: 'Cross-worktree lease is last-writer-wins: a stale worktree''s scope change
  reverts a narrowed lease to its old superset'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The shared cross-worktree lease file (`.git/frob-leases/<id>.json`) is
re-recorded by `mutate_scope` from whichever worktree happens to run a
scope change, using THAT worktree's own view of the ticket's scope. When
two worktrees hold divergent copies of the same ticket's ledger entry,
the last writer wins -- and it can overwrite a correct narrow scope with
a stale broad one.

TWO INDEPENDENT OBSERVATIONS, 2026-08-10, both on T-1696:

1. Coordinator: ran `frob ticket scope T-1696 --remove src/frob/tickets/_land.py
   --remove src/frob/app/ticket_runner/_land_cmd.py` from the ROOT checkout.
   The ledger updated correctly (scope became 2 paths). The lease file
   still listed all 4 paths afterwards. Notably a probe
   (`scope T-1638 --add src/frob/tickets/_land.py`) SUCCEEDED at that
   moment despite the stale lease naming that path.
2. A different agent, later: the SAME stale lease BLOCKED its
   `scope --add src/frob/app/ticket_runner/_land_cmd.py`. It resolved it
   by calling `frob.tickets._leases.record_lease` directly from the
   `profile-collapse` worktree with that worktree's current scope --
   re-triggering the existing primitive, not hand-editing anything.

The contradictory symptoms (one blocked, one not) are the tell: the
lease file's contents depend on which worktree last touched the ticket,
so the same stale entry can appear to block or not depending on timing.

MECHANISM: `mutate_scope` re-records the lease only
`if updated.state is TicketState.IN_PROGRESS`, using `updated.scope` --
the scope as seen in the CALLING worktree. The `profile-collapse`
worktree had never merged the coordinator's narrowing commit (verified:
`git merge-base --is-ancestor <narrowing-sha> <worktree HEAD>` is false,
and that worktree's own `tickets/T-1696/ticket.md` still carried the
broad scope plus an independently-added path). So any scope-affecting
operation there rewrote the shared lease back to the old broad set.

WHY IT MATTERS: the lease is the cross-worktree exclusion mechanism under
parallel dispatch. A lease that can silently revert to a superset blocks
other agents from paths nobody is editing -- this cost one agent a
blocked `scope --add` and cost the coordinator a wrong diagnosis (I
initially concluded the narrowing had silently failed).

DO NOT FIX IT THIS WAY:
- Do NOT make the lease file authoritative over the ledger. The ledger is
  the source of truth; the lease is a derived side-channel.
- Do NOT drop the `IN_PROGRESS` guard so every scope change rewrites the
  lease -- that makes the last-writer-wins race MORE likely, not less.
- Do NOT have agents call `record_lease` by hand as the standing remedy.
  It worked as a one-off repair here, but a manual resync step is exactly
  the kind of knowledge-requiring workaround that does not survive.

FIX DIRECTION: derive the lease from the ledger at READ time rather than
caching it at write time, or make the recorded lease carry the ledger
commit it was derived from so a reader can detect that it is stale
relative to main. Either removes last-writer-wins entirely.

ACCEPTANCE: first test must FAIL before the fix -- two worktrees with
divergent copies of one in-progress ticket; narrow the scope in worktree
A, run any scope-affecting operation in worktree B, and assert the
effective lease does NOT revert to B's stale broader set. Then assert a
legitimate scope expansion from the owning worktree still takes effect.
