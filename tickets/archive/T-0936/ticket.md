---
id: T-0936
title: migrate existing EPIC-titled tickets to tier=epic
state: done
kind: docs
origin: human
created: '2026-07-26'
priority: medium
blocked_by:
- T-1070
- T-1069
parent: T-0715
tier: ticket
sprint: null
scope:
- tickets.md
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- 'cmd:grep -c ''tier: epic'' tickets.md exit=0 sha256=06e9d52c1720'
designated_repro_test: null
threat: null
component: null
---
T-0715's user mandate asked for existing EPIC-titled tickets to get
`tier: epic` mechanically as part of the migration to the new
`TicketTier` field (landed by T-0715 itself). This ticket is the actual
one-time backfill: scan `tickets.md`/`tickets-archive.md` for tickets
whose title matches the repo's existing "EPIC" naming convention (case-
insensitively prefixed, e.g. titles starting "EPIC:" or "EPIC "), set
their `tier` field to `epic` via the normal `frob ticket` write path (not
a hand-edit), and record the count changed in the Done report. Also worth
deciding here (not decided by T-0715): whether direct children of an
epic-titled ticket should default to `tier: story` at the same time, or
whether that requires a human judgment call per ticket.

Acceptance: GIVEN the ledger as it stood at T-0715 land WHEN this
migration runs THEN every ticket whose title matched the EPIC convention
carries `tier: epic` afterward, and no other ticket's tier changed.