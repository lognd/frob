---
id: T-3245
title: Post-land sweep files byte-identical duplicate tickets (T-3236/T-3237, third
  confirmed instance)
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
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
The post-land sweep files BYTE-IDENTICAL duplicate tickets. Third confirmed
instance; the first two were observed but the mechanism was never found and
never ticketed.

MEASURED 2026-08-28:

    diff <(grep -v "^id:" tickets/T-3236/ticket.md) \
         <(grep -v "^id:" tickets/T-3237/ticket.md)
    -> no output. IDENTICAL apart from the id field.

Both were created 2 seconds apart (05:18:51 and 05:18:53), both name the same
single identity (OPAQUE001 tests/test_vet_capability.py), both attribute it to
the same commit (T-2885 at 70e20f4c2ce9).

PRIOR INSTANCES, same shape, both found earlier this drive and both closed
without the mechanism being identified: T-3158/T-3159, and T-3022/T-3023 (same
title AND same body). Series CP looked for the duplicate-filing code path and
correctly declined to guess rather than inventing a cause. That deferral is now
three instances old and should be closed out.

WHY THIS COSTS MORE THAN ONE WASTED TICKET. Each duplicate consumes a full agent
triage cycle -- read, reproduce, measure, close, land -- for a finding that
another agent is triaging simultaneously. Two agents can also race on the same
underlying fix. And it corrupts the queue's own signal: an operator counting
open regressions double-counts.

DO NOT FIX THIS BY DEDUPING AFTER THE FACT. A post-hoc "delete tickets with
identical bodies" pass would paper over a filing path that runs twice, and would
be dangerous besides -- two sweeps legitimately CAN find the same (rule, file)
identity at different commits, and those are not duplicates.

MEASURE FIRST, DO NOT ASSUME. Candidate mechanisms, none verified:
  - The deferred sweep (T-1684) is spawned more than once for the same land, so
    two detached processes race and both file.
  - The already-owned check in `_file_regression_ticket` (which returns None
    when every finding attributes to an already-open ticket) does not see the
    sibling ticket because it was filed microseconds earlier and the ledger read
    is stale.
  - Ticket-id allocation succeeds twice against a stale merge-base view -- there
    is a known prior defect of exactly this shape in the allocator.

The 2-second gap is the strongest available clue and points at a race rather
than a re-run; say what the evidence actually supports.

RELATED, IN SCOPE TO REPORT BUT NOT TO FIX HERE: T-3236's body records that its
own file-time re-measure was unmeasurable ("spawn refused/timeout/unparsable"),
so it took T-3222's documented fail-open path. That posture is CORRECT and must
not be changed -- unmeasurable is never read as resolved. But it means the
T-3222 liveness gate delivered no benefit on this run. Report how often that
path is taken across recent sweeps; if it is common, the gate is mostly inert in
practice and that deserves its own ticket.

ACCEPTANCE
- The duplicate-filing mechanism identified, with evidence -- not a plausible
  story.
- A must-fire fixture: two concurrent/duplicated sweeps for one land produce ONE
  ticket.
- A must-stay-quiet fixture: two sweeps finding the same (rule, file) identity
  at DIFFERENT commits still produce two tickets. These are not duplicates and
  suppressing them would be a regression.
- A stated count of how often the T-3222 re-verify goes unmeasurable in recent
  sweeps, filed separately rather than fixed here.
