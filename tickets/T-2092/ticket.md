---
id: T-2092
title: Renumber allocates ids without allocator_lock, so a renumbered ticket can collide
  with a concurrent new and be silently deleted by a merge
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_renumber_v2.py
- src/frob/tickets/_new_renumber.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given a renumber and a concurrent frob ticket new both allocating an id, when
    both complete, then they hold DIFFERENT ids -- this test MUST fail against current
    main, where renumber takes no allocator_lock
  evidence: []
- text: given two ticket records that nonetheless claim the same id, when the ledger
    is loaded or checked, then this is reported as an error rather than silently resolved
    by picking one
  evidence: []
- text: given a branch carrying a ticket file that a merge of main would overwrite
    with different content for the same id, when the merge happens during a land,
    then the collision is surfaced rather than silently resolved
  evidence: []
threat: null
component: tickets
labels:
- data-loss
anchor: false
anchor_reason: null
---
## What happened (measured, this session)

T-2083's agent finished its ticket and filed a follow-up for the half it had
to cut (the LAND-PROOF surfacing work). Its draft was promoted, then
**renumbered mid-land after an id collision**, landing on `T-2090`. At
almost the same moment I filed an unrelated ticket via `frob ticket new`,
which was also allocated `T-2090`. When the agent merged main into its
worktree to land, my `tickets/T-2090/ticket.md` won and the agent's ticket
file was overwritten.

**The follow-up ticket was lost entirely.** Verified after the fact:

    git show --stat 213eef2f3009      # T-2083's land: no follow-up ticket file
    grep -m1 '^title:' tickets/T-2090/ticket.md
      -> "Evidence collection discards the missing_natives..."   (MINE)
    grep -m1 '^title:' .claude/worktrees/t-2083-land-verify/tickets/T-2090/ticket.md
      -> same, MINE -- the merge overwrote the agent's copy in its own worktree too

Its content survived only in the agent's final report, from which I had to
reconstruct and re-file it (now T-2091). Had that report been shorter, or
had nobody read it, the work would have vanished silently: no gate fires for
a ticket that was never written, and the ticket it was cut from had already
landed marked done.

## Root cause, read from source

T-1669 (landed `f611f8f8b`) fixed id allocation by wiring the pre-existing
but never-wired `allocator_lock` (T-1253, `.frob/tickets-allocator.lock`)
into BOTH draft-promotion paths -- `finalize_draft` and
`finalize_draft_for_land` in `src/frob/tickets/_draft_finalize.py:124,192`.

It did not cover the RENUMBER path, which is a third allocator:

    $ grep -c allocator_lock src/frob/tickets/_renumber_v2.py
    0
    $ grep -c allocator_lock src/frob/tickets/_new_renumber.py
    0

`_renumber_v2.py:298` takes only `ticket_lock(root, lock_id)` -- a
per-ticket lock, which serialises writes to ONE ticket and says nothing
about whether the target id is free. So a renumber picking a "currently
free" id races any concurrent `frob ticket new` picking the same id, exactly
as `finalize_draft` raced `finalize_draft_for_land` before T-1669.

## Prior occurrences of the same class

- T-2060 had to be renumbered TWICE mid-flight: ids T-2041 and T-2045 were
  each claimed by a concurrent land between promotion and land attempt.
- An earlier session: an agent guessing the next free id collided with real
  ticket T-1651 and silently mis-attributed SEVEN `frob:ticket` edges.
- Today: an agent fabricated placeholder `T-2043`, a real unrelated ticket,
  stamping 7 false edges (caught by hand before landing).
This one is worse than all three, because the outcome was not a mis-binding
that a reader could notice -- it was silent deletion.

## DO NOT FIX IT THIS WAY

- **Do not fix only the lock.** Taking `allocator_lock` in renumber closes
  the race for FUTURE allocations, but does nothing about the second half of
  this incident: a ticket file being silently overwritten by a merge. Two
  tickets briefly shared an id and git resolved it by picking one, with no
  conflict and no warning. A collision must be detectable AFTER the fact,
  not only prevented before it.
- **Do not resolve a duplicate id by picking a winner.** That is precisely
  what happened. If two different ticket bodies ever occupy one id, that is
  a hard error requiring both to be preserved.
- **Do not rely on the renumbering agent noticing.** This agent did
  everything right -- it detected the first collision, renumbered rather
  than forcing, and disclosed the whole sequence in its report. It still
  lost the ticket, because the loss happened in a merge after its last
  check.
- **Do not treat "the report mentioned it" as recovery.** I recovered this
  by reading a long agent report closely. That is not a mechanism.

## Acceptance direction

The first test must fail against current main: two concurrent id-allocating
operations, at least one of them a RENUMBER, must not be able to produce the
same id. Separately, a detector for two ticket directories claiming one id
(or a ticket id present in a branch and overwritten by a merge) would have
turned this silent loss into a visible failure -- if that belongs in a
sibling ticket, file it and say so.
