---
id: T-1669
title: 'Ledger ownership model: lease-scoped writes plus atomic draft promotion at
  land'
state: queued
kind: feature
origin: human
created: '2026-08-06'
priority: critical
blocked_by:
- T-1631
parent: T-1136
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner/**
- docs/design/ledger-v2.md
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The design the repo owner specified 2026-08-06: "apart from the frob ticket commands, main's regular tickets never get overwritten by a worktree, and on land, the draft tickets are automatically converted atomically into main tickets and committed. I don't want any manual handling of tickets."

THE ROOT CAUSE OF EVERY TICKET-HANDLING FAILURE THIS DRIVE IS THE V1 MONOFILE.

One `tickets.md` holds every ticket's record. Every worktree has a copy. Every `frob ticket` command writes the local copy. Git then merges STRUCTURED RECORDS LINE-WISE. Everything that went wrong follows directly from that:
- a `kind` field changed and committed on main was silently dropped by a later merge, with no conflict marker (T-1617) -- the land then read the stale value and refused
- draft blocks vanish across land previews (T-0577), so every follow-up ticket an agent files must be refiled by hand
- the manual refile recipe deletes the block holding the ticket's evidence and Done report (T-1637) -- it destroyed T-1636's and recovery needed `git show <commit>~1:tickets.md`
- duplicate blocks after merges, repaired by hand-splicing python over the ledger
- 33 active-vs-archive duplicate blocks needing manual repair in one earlier session

None of these are workflow mistakes to be more careful about. They are what happens when a structured, per-record datastore is stored as one text file and merged textually.

THE MODEL:

1. OWNERSHIP. A ticket's record is writable only by the holder of its lease.
   - a worktree holding T-1234's lease may write T-1234 and nothing else
   - main must REFUSE to write a ticket currently leased to a worktree (this is the half that lost the kind field -- main edited a ticket a worktree owned)
   - a ticket with no lease is main's to write
   Enforcement under v2 is a path check: refuse a commit touching `tickets/T-####/` you do not hold. Under v1 it is not enforceable at all, which is the argument for prioritising the migration.

2. PROMOTION AT LAND. Drafts stay local and opaque in the worktree; `frob ticket land` converts them atomically.
   A worktree cannot safely allocate a global id -- that needs coordination, and coordination is what breaks (an agent guessing the next free id collided with real ticket T-1651 this session, silently mis-attributing seven frob:ticket edges). The land already runs against main and, with T-1619's lease, holds exclusive access. That is exactly where an id CAN be allocated race-free. So: allocate at land, rewrite the draft record and every citation (ledger and source), commit as part of the land transaction. `frob ticket renumber` already performs the rewrite half atomically and should be reused rather than reimplemented.

3. NO MANUAL HANDLING. The acceptance criterion is the owner's sentence. If any flow still requires a human or coordinator to edit the ledger, extract a body, swap a citation, or delete a block, that flow is not done.

WHY V2 MAKES THIS NATURAL RATHER THAN BOLTED ON:
- one file per ticket -> ownership is a path check
- merging main into a worktree cannot conflict on other tickets, because they are different files
- promotion is `git mv tickets/T-draft-xxxx tickets/T-1234`, genuinely atomic
- a lost field requires two writers to the SAME file, which the ownership rule forbids

SEQUENCING: T-1631 migrates main's own ledger to v2 (coordinator task, quiet window, `frob ticket migrate --to v2`). T-1552 then deletes the v1 splice machinery. The ownership check and promotion path should be built correct-on-v2 and merely non-breaking on v1 -- do not design around the monofile that is being retired.