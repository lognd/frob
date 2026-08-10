## Done report

`write_archive`'s v2 branch was v1-only, so `frob ticket archive` would
have lost tickets in a v2 repo. That mattered urgently: TICK003 forces an
archive roughly every 60 closed tickets, and one run earlier the same day
moved 62 tickets at once. Migrating to v2 with this unfixed meant the
next forced archive silently dropping them, which is why the v2 migration
(T-1631) was blocked on this ticket.

The core fix (`_write_archive_v2`, upserting through
`write_archived_ticket` and pruning stale dirs to match what
`load_archive`'s v2 reader expects) reached main via an untracked commit
rather than through this ticket, so the ledger continued to claim the
work was queued.

What this close adds is the acceptance bar the ticket was actually
gating: proof that a real archive ROUND-TRIPS both count and content, not
merely that the command exits 0. A wholesale-replace primitive that
truncated a body while preserving the id set would pass every other test
in that class undetected.

Verified two ways before the migration ran, rather than trusting either
the report or the ledger:

- Independently, in a throwaway v2 repo: 40 tickets written through
  `write_archive`, 40 read back, count and per-ticket title/body/state
  intact.
- The bound test itself, `test_v2_write_archive_round_trips_many_tickets_
  count_and_content`, asserting count, key set, and title/body/state per
  id across 40 archived tickets.

That test had to be recovered surgically. Its land commit (c3fdab30) was
never an ancestor of main -- it was built on a stale base, and merging it
wholesale would have deleted 1723 lines of other agents' landed work. The
test was extracted from that branch and applied to current main instead.

frob:no-behavior-change -- the production fix was already on main; this
change adds only the test that proves it and this record. The behaviour
under test was independently exercised before landing, so there is no
fail-at-parent delta to reproduce.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_write_archive_round_trips_many_tickets_count_and_content` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 1559 warning(s), 724 waived
- error-findings: none (measured, zero errors)
