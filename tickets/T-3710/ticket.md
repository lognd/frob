---
id: T-3710
title: T-0450 archive/active ledger desync causes DuplicateId on any write
state: queued
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-0450/
- tickets/archive/T-0450/
- src/frob/tickets/
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
found while working the AW self-gate floor drive (TICK003/TICK004 cleanup, 2026-09-02).

T-0450 (REF002 systematic categories bug, created 2026-07-20, queued) is
present in the ledger as an active QUEUED ticket -- frob ticket show
T-0450 resolves it, and gate:TICK TICK004 flags it as rotting queued
backlog -- but tickets/archive/T-0450/ticket.md ALSO exists on disk
(added by commit d04ac2d93 'chore(tickets): show T-0450', predating this
session). The active-tree file tickets/T-0450/ticket.md does not exist
until a write command (frob ticket priority T-0450 <level>) creates it
fresh, at which point BOTH the archive and active copies exist
simultaneously and every subsequent frob ticket command (show, priority,
check --only tickets, etc) fails hard with:

  ERROR: tickets: id(s) {'T-0450'} present in both active and archive
  ERROR: <verb> failed: DuplicateId: Ticket id already exists

Reproduced live: frob ticket priority T-0450 low succeeded and committed
a brand-new tickets/T-0450/ticket.md (42 lines) even though T-0450 was
already archived; the very next ticket command (frob ticket priority
T-1382 low) then failed with DuplicateId because both copies now
existed. Recovered by git revert of the priority-T-0450 commit, which
deleted the newly-materialized active file and restored T-0450 to its
prior (archive-only, but still ledger-resolvable-as-queued) state --
this reproduces on any future write to T-0450 until the underlying
desync is fixed.

Root cause is presumably one of: (a) T-0450 was archived by a stale/buggy
archive run despite never reaching a closed (done/dropped) state, and
the active ledger row was never removed alongside the archived file, or
(b) the ticket-loading path resolves an id from tickets.md independent
of which directory the id's ticket.md file physically lives in, so a
write verb naively creates a fresh active-tree file without checking the
archive tree first.

Left as a disclosed gap: T-0450 could not be re-prioritized as part of
this drive's TICK004 cleanup (T-1382 and T-2799 were both
re-prioritized cleanly; T-0450's own gate finding is left as residual,
reported to the user) -- fixing the archive/active desync itself is
outside this ticket's narrow TICK003/TICK004 scope.