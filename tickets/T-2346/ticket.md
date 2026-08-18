---
id: T-2346
title: tickets.md disagrees with the per-ticket ledger on 21 ticket states, always
  claiming finished work is still open
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: high
blocked_by:
- T-2356
parent: null
tier: ticket
sprint: null
runs_last: false
evidence_scope:
- tests/test_tickets_migration.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back
- tests/test_tickets_migration.py::TestMigrateMissingV2::test_a_stale_active_row_whose_v2_state_already_moved_to_archive_is_not_duplicated
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors
designated_repro_test: null
acceptance:
- text: given a ticket whose state changed via the CLI, when both tickets.md and tickets/<ID>/ticket.md
    are read, then they agree (or tickets.md no longer exists)
  evidence:
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors
- text: 'given the 108 tickets whose stale tickets.md row implied no per-ticket file,
    when checked against BOTH tickets/<id>/ticket.md and tickets/archive/<id>/ticket.md,
    then all 158 tickets.md ids already have a real v2 file somewhere (T-2355 measured
    2026-08-17: zero missing in either location) -- no migration write was needed
    or made'
  evidence:
  - tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back
  - tests/test_tickets_migration.py::TestMigrateMissingV2::test_a_stale_active_row_whose_v2_state_already_moved_to_archive_is_not_duplicated
- text: given a deliberately divergent row, when the gate runs, then the divergence
    is reported rather than passing silently
  evidence:
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors
acceptance_amendments:
- op: replace
  index: 1
  old_text: given the 108 tickets that exist only in tickets.md with no per-ticket
    file, when the fix is applied, then none of them is lost
  new_text: 'given the 108 tickets whose stale tickets.md row implied no per-ticket
    file, when checked against BOTH tickets/<id>/ticket.md and tickets/archive/<id>/ticket.md,
    then all 158 tickets.md ids already have a real v2 file somewhere (T-2355 measured
    2026-08-17: zero missing in either location) -- no migration write was needed
    or made'
  reason: 'T-2355 (child, done) found and fixed the coordinator''s own filing error:

    "108 tickets exist only in tickets.md with no per-ticket file" was

    measured by checking only tickets/T-####/ (active v2 dir) and never

    tickets/archive/<id>/. Direct verification against the real repo tree

    (all 158 tickets.md ids checked against BOTH v2 locations) found zero

    missing a v2 file -- all 108 already had an ARCHIVED v2 file, just not

    where the stale monofile row implied. There is no 108-ticket migration

    gap; this criterion is corrected to reflect that, rather than left to

    silently mislead a future reader.

    '
  actor: logan
  at: '2026-08-17'
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17, after an implementer lost real time to it.

The monolithic `tickets.md` ledger and the per-ticket `tickets/T-####/
ticket.md` files disagree about ticket STATE, and `tickets.md` is the stale
side. Measured across the whole file:

    tickets present in tickets.md:            158
    of those, no per-ticket file exists:      108   (pre-migration only)
    STATE DIVERGENCES:                         21

Every divergence runs the same direction -- `tickets.md` says the ticket is
open, the per-ticket file says it is finished:

    T-1226  tickets.md=queued   per-ticket=done
    T-1238  tickets.md=queued   per-ticket=done
    T-1315  tickets.md=queued   per-ticket=done
    T-1344  tickets.md=queued   per-ticket=done
    T-1480  tickets.md=queued   per-ticket=done
    T-1552  tickets.md=queued   per-ticket=dropped
    T-1556  tickets.md=queued   per-ticket=done
    T-1557  tickets.md=queued   per-ticket=dropped
    T-1584  tickets.md=queued   per-ticket=done
    T-1585  tickets.md=queued   per-ticket=done
    T-1621  tickets.md=queued   per-ticket=done
    T-1623  tickets.md=queued   per-ticket=done
    T-1664  tickets.md=planned  per-ticket=done
    T-1665  tickets.md=planned  per-ticket=done
    ... 21 total

WHY THIS COSTS REAL TIME: anyone -- human or agent -- who reads `tickets.md`
to answer "is this done?" gets a wrong answer for 21 tickets, always in the
direction of redoing finished work. An implementer hit exactly this today
while measuring the T-1662 epic: T-1664/T-1665 read `planned` in
`tickets.md` while both were actually `done`, and the time went into
discovering the file was lying rather than into the work. `tickets.md` is
also the obvious file to grep -- it is one file rather than 465 directories
-- so it is precisely what a newcomer or a quick script will reach for.

This is the repo's own no-duplication rule violated in its own ledger: two
copies of the same fact, one of which has silently desynced.

REQUIRED -- pick ONE and make it true, do not patch the symptom:
 (a) If `tickets/T-####/ticket.md` is the source of truth (it is -- the v2
     ledger design says so and the CLI writes it), then `tickets.md` must
     either be REGENERATED from the per-ticket files by the same code paths
     that write them, or DELETED. A hand-maintained mirror will desync
     again the moment anyone forgets.
 (b) If `tickets.md` must survive for a reader that cannot walk the
     directories, generate it as a derived artifact and add a gate that
     FAILS when it diverges from the per-ticket files -- the same posture
     this repo takes for every other derived artifact.
Do NOT simply hand-correct the 21 rows. That restores the value without
fixing the mechanism, and the next land desyncs it again.

INVESTIGATE FIRST: find out which writes still touch `tickets.md` and which
only touch the per-ticket file. The divergence set is entirely
pre-2026-08 ids, which suggests the split happened at the v2 migration and
`tickets.md` simply stopped being updated for migrated tickets -- confirm
that before designing the fix.

POSITIVE CONTROLS: (1) after the fix, a state change made via the CLI is
visible in BOTH representations (or the stale one is gone); (2)
must-still-pass -- the 108 tickets that exist ONLY in `tickets.md`, with no
per-ticket file, are not lost by whatever you do; (3) a deliberately
divergent row is DETECTED, if you take direction (b).