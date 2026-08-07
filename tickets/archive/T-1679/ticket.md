---
id: T-1679
title: 'Invert the content-loss guard default: refuse, and give test fixtures an explicit
  unchecked primitive'
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- src/frob/tickets/_models.py
- tests/unit/test_ticket_store.py
- tests/test_ticket_land.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_store.py
  reason: invert write_ticket content-loss default to strict; add _write_ticket_unchecked
    escape hatch for test fixtures
  actor: logan
  at: '2026-08-06'
- op: add
  glob: src/frob/tickets/_models.py
  reason: invert write_ticket content-loss default to strict; add _write_ticket_unchecked
    escape hatch for test fixtures
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: invert write_ticket content-loss default to strict; add _write_ticket_unchecked
    escape hatch for test fixtures
  actor: logan
  at: '2026-08-06'
- op: add
  glob: tests/test_ticket_land.py
  reason: invert write_ticket content-loss default to strict; add _write_ticket_unchecked
    escape hatch for test fixtures
  actor: logan
  at: '2026-08-06'
- op: add
  glob: docs/modules/tickets.md
  reason: invert write_ticket content-loss default to strict; add _write_ticket_unchecked
    escape hatch for test fixtures
  actor: logan
  at: '2026-08-06'
evidence:
- tests/unit/test_ticket_store.py::TestWriteTicket::test_content_loss_refuses_by_default
- tests/unit/test_ticket_store.py::TestWriteTicket::test_non_strict_opt_out_warns_loudly_instead_of_refusing
- tests/unit/test_ticket_store.py::TestWriteTicketUnchecked::test_skips_the_content_loss_guard_entirely
- tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference::test_report_side_still_wins_when_it_also_outranks_the_reportless_side
- tests/test_ticket_land.py::TestTick005LandRegressions::test_detects_terminal_ticket_regressed_to_non_terminal
designated_repro_test: null
threat: null
component: null
---
T-1637 added _check_no_content_loss in src/frob/tickets/_store.py -- a guard on write_ticket that catches a write replacing a ticket's evidence list AND Done report with nothing. That is the exact shape of the T-1636 field incident, which discarded 12 evidence ids and a 12KB Done report recoverable only by git archaeology.

It ships with strict=False as the DEFAULT, so the guard WARNS and proceeds; only 'frob ticket promote' opts into refusing. That means the incident it was written to prevent would still happen today, just with a log line attached. A guard whose default is to allow the thing it detects is a detector, not a guard.

The stated reason for the warn-default is that a hard refuse broke six pre-existing splice_ledger test fixtures that deliberately construct a 'poorer' ticket snapshot via write_ticket. That is a real constraint, but it argues for a different seam, not a weaker default: test fixtures wanting to simulate a regressed ledger side should call an explicitly-named unchecked primitive (e.g. _write_ticket_unchecked) that says so at the call site, leaving write_ticket itself safe for every production caller.

Work:
1. Add the explicit unchecked primitive and move the six fixtures onto it.
2. Flip write_ticket's default to strict (refuse).
3. Audit every remaining production call site for one that legitimately needs to empty both fields; each such site opts out explicitly and says why.

Test convenience must not set the safety level of a production write path. Filed by the coordinator while reviewing T-1637 before landing it -- the guard is a real improvement and lands as-is; this ticket finishes it.