---
id: T-2092
title: Renumber allocates ids without allocator_lock, so a renumbered ticket can collide
  with a concurrent new and be silently deleted by a merge
state: done
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
- tests/test_tickets_ledger_concurrency.py
- tickets/T-2101/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_ledger_concurrency.py
  reason: concurrency repro test for the renumber-vs-new_ticket allocation race lives
    here, following this file's own precedent (TestPromoteVsLandFinalizeAllocationRace
    etc.)
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2101/**
  reason: filing this ticket's own follow-up draft (half 2 of T-2092) touches its
    own new ticket.md, same as any frob ticket new call
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_tickets_ledger_concurrency.py::TestRenumberVsNewTicketAllocationRace::test_renumber_and_concurrent_new_ticket_never_allocate_the_same_id
designated_repro_test: tests/test_tickets_ledger_concurrency.py::TestRenumberVsNewTicketAllocationRace::test_renumber_and_concurrent_new_ticket_never_allocate_the_same_id
acceptance:
- text: given a renumber and a concurrent frob ticket new both allocating an id, when
    both complete, then they hold DIFFERENT ids -- this test MUST fail against current
    main, where renumber takes no allocator_lock
  evidence:
  - tests/test_tickets_ledger_concurrency.py::TestRenumberVsNewTicketAllocationRace::test_renumber_and_concurrent_new_ticket_never_allocate_the_same_id
- text: 'DO NOT accept "verify the target id is free before renumbering/allocating"
    (a checklist/procedural discipline, documentation, or manual double-check) as
    a fix for this ticket. Measured FOUR TIMES in one day (2026-08-10), including
    twice by agents who performed exactly that verification correctly and diligently
    (occurrence 4: two agents independently checked T-2096 was free, both got the
    same correct answer, both claimed it, one landed first) -- check-then-claim across
    two roots/worktrees is not atomic no matter how careful the check is. Only a real
    lock (or an equivalent atomic claim primitive) closes this; a "verify first" remedy
    must be rejected on sight for this ticket.'
  evidence:
  - tests/test_tickets_ledger_concurrency.py::TestRenumberVsNewTicketAllocationRace::test_renumber_and_concurrent_new_ticket_never_allocate_the_same_id
acceptance_amendments:
- op: remove
  index: 2
  old_text: given a branch carrying a ticket file that a merge of main would overwrite
    with different content for the same id, when the merge happens during a land,
    then the collision is surfaced rather than silently resolved
  new_text: null
  reason: 'Split per this ticket''s own body ("If half 2 turns out to be genuinely

    large, implement half 1, measure and report, and file half 2 as its own

    ticket"). This criterion is the "detect a duplicate id after the fact"

    half: it needs a real merge-time or history-scanning detector across

    tickets/**/ticket.md, distinct from the allocator_lock fix this ticket

    implements, and is genuinely separate engineering scope. Filed as

    T-2101 with this session''s own repro evidence cited.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 1
  old_text: given two ticket records that nonetheless claim the same id, when the
    ledger is loaded or checked, then this is reported as an error rather than silently
    resolved by picking one
  new_text: null
  reason: 'Split per this ticket''s own body ("If half 2 turns out to be genuinely

    large, implement half 1, measure and report, and file half 2 as its own

    ticket"). This criterion is the "detect a duplicate id after the fact"

    half: it needs a real merge-time or history-scanning detector across

    tickets/**/ticket.md, distinct from the allocator_lock fix this ticket

    implements, and is genuinely separate engineering scope. Filed as

    T-2101 with this session''s own repro evidence cited.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 10
  old_text: rejected on sight for this ticket.
  new_text: null
  reason: 'Accidental split: --criterion-file split this single criterion into 10
    by

    newline instead of blank-line-delimited blocks (my mistake, not a policy

    change) -- removing to re-add as one criterion.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 9
  old_text: atomic claim primitive) closes this; a "verify first" remedy must be
  new_text: null
  reason: 'Accidental split: --criterion-file split this single criterion into 10
    by

    newline instead of blank-line-delimited blocks (my mistake, not a policy

    change) -- removing to re-add as one criterion.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 8
  old_text: no matter how careful the check is. Only a real lock (or an equivalent
  new_text: null
  reason: 'Accidental split: --criterion-file split this single criterion into 10
    by

    newline instead of blank-line-delimited blocks (my mistake, not a policy

    change) -- removing to re-add as one criterion.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 7
  old_text: landed first) -- check-then-claim across two roots/worktrees is not atomic
  new_text: null
  reason: 'Accidental split: --criterion-file split this single criterion into 10
    by

    newline instead of blank-line-delimited blocks (my mistake, not a policy

    change) -- removing to re-add as one criterion.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 6
  old_text: T-2096 was free, both got the same correct answer, both claimed it, one
  new_text: null
  reason: 'Accidental split: --criterion-file split this single criterion into 10
    by

    newline instead of blank-line-delimited blocks (my mistake, not a policy

    change) -- removing to re-add as one criterion.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 5
  old_text: 'correctly and diligently (occurrence 4: two agents independently checked'
  new_text: null
  reason: 'Accidental split: --criterion-file split this single criterion into 10
    by

    newline instead of blank-line-delimited blocks (my mistake, not a policy

    change) -- removing to re-add as one criterion.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 4
  old_text: including twice by agents who performed exactly that verification
  new_text: null
  reason: 'Accidental split: --criterion-file split this single criterion into 10
    by

    newline instead of blank-line-delimited blocks (my mistake, not a policy

    change) -- removing to re-add as one criterion.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 3
  old_text: as a fix for this ticket. Measured FOUR TIMES in one day (2026-08-10),
  new_text: null
  reason: 'Accidental split: --criterion-file split this single criterion into 10
    by

    newline instead of blank-line-delimited blocks (my mistake, not a policy

    change) -- removing to re-add as one criterion.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 2
  old_text: (a checklist/procedural discipline, documentation, or manual double-check)
  new_text: null
  reason: 'Accidental split: --criterion-file split this single criterion into 10
    by

    newline instead of blank-line-delimited blocks (my mistake, not a policy

    change) -- removing to re-add as one criterion.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  index: 1
  old_text: DO NOT accept "verify the target id is free before renumbering/allocating"
  new_text: null
  reason: 'Accidental split: --criterion-file split this single criterion into 10
    by

    newline instead of blank-line-delimited blocks (my mistake, not a policy

    change) -- removing to re-add as one criterion.

    '
  actor: logan
  at: '2026-08-10'
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