---
id: T-2355
title: 'Ledger v2 migration: build the golden round-trip test and migrate the 108
  legacy-only tickets'
state: queued
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: T-2346
tier: ticket
sprint: null
runs_last: false
scope:
- tickets/**
- tests/fixtures/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Investigated for T-2346 (measured 2026-08-17): confirmed hypothesis --
this is NOT a fresh bug, it is an INCOMPLETE, already-designed migration.
docs/design/ledger-v2.md (T-1136) specifies exactly this shape:
`_store_mode(root)` already treats this repo as "v2" (any `tickets/T-####/
ticket.md` makes it so, section 1/`_v2_glob`), and section 7's migration
plan explicitly says the migrator "does NOT delete `tickets.md`/
`tickets-archive.md` in the same commit -- it leaves them as an inert
byte-for-byte snapshot until a human confirms the v2 tree round-trips
cleanly, then a SEPARATE commit deletes the monofiles." That confirmation
+ deletion step was never done. The 21 state-divergent rows and 108
tickets-only-in-tickets.md are exactly what "never finished cutover"
looks like -- writes for a migrated ticket go to `tickets/<ID>/ticket.md`
only (confirmed: `git log --grep T-1664` shows `tickets/T-1664/ticket.md`
touched by every state-changing commit, never `tickets.md`), while
tickets.md was frozen at whatever state it held when each ticket was
individually migrated or simply never touched again.

This is child 1 of 2 (see the paired ticket for the final cutover/
deletion step, which depends on this one). This ticket:

1. Build the golden round-trip fixture + test docs/design/ledger-v2.md
   section 7.3 specifies but flags as not-yet-built (`tests/fixtures/
   tickets/golden-monofile-ledger.md` + a round-trip test asserting
   monofile -> v2 -> monofile-rendering produces an equal `dict[str,
   Ticket]` + equal Done-report bodies, not necessarily byte-identical).
2. Run (or extend) `frob ticket migrate --to v2` against the 108 tickets
   that exist ONLY in `tickets.md` today (no `tickets/<ID>/ticket.md`),
   producing a real per-ticket file for each -- verify none are lost
   (acceptance[1] on the parent ticket) and each round-trips per the
   golden test's own equivalence check.
3. For the 21 already-migrated-but-divergent tickets (T-1664/T-1665/
   T-1226/etc.), the per-ticket file is already the correct, current
   state -- do NOT touch it; this step is only about tickets.md's stale
   duplicate row, which the paired cutover ticket resolves by deleting
   the whole file, not by hand-editing 21 rows (T-2346's own explicit
   instruction: do not patch the symptom).

Positive control: after this lands, `tickets/*/ticket.md` covers all 158
ids `tickets.md` currently lists (158 directories, up from ~50 today --
verify the exact starting count fresh, it may have moved since
measurement), and the golden round-trip test passes on a fixture built
from THIS repo's real pre-migration tickets.md content, not a synthetic
toy.
