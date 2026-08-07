---
id: T-1631
title: 'coordinator: migrate main''s own ledger to v2 in a quiet window'
state: in-progress
kind: feature
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1583
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
- tickets-archive.md
- tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_migration.py::TestMigrateV1ToV2::test_golden_round_trip_semantic_equality
- tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_write_archive_round_trips_many_tickets_count_and_content
designated_repro_test: null
threat: null
component: null
---
T-1552's own precondition (main's ledger migrated to v2) is not yet met:
this repo's tickets.md/tickets-archive.md are still the v1 monofile as of
2026-08-06 (verified directly: tickets.md/tickets-archive.md exist at
repo root, no tickets/T-####/ticket.md directories exist). T-1492 (CLI
wiring for `frob ticket migrate --to v2`) and T-1553 (fresh-repo default
flip) are both done, but nobody has actually RUN the migration against
this repo's own ledger content yet.

This is a coordinator-only action (needs a quiet window with zero
in-flight worktrees, per T-1552's own stated precondition -- a worktree
mid-ticket-mutation during the migration would race the wholesale
rewrite). Filed while working T-1552 so its blocker has a concrete id
instead of a prose-only precondition.

Plan (from T-1552's own Description):
1. Coordinator runs `frob ticket migrate --to v2` against this repo in a
   quiet window (zero in-flight worktrees).
2. Observe the LEDGERV1001 deprecation window for the recorded interval.
3. Once stable, T-1552 unblocks and can delete the v1 splice machinery.