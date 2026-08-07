---
id: T-0184
title: frob ticket close prints ERROR MissingEvidence but exits 0
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_without_evidence_fails
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_with_evidence_and_done_report_succeeds
designated_repro_test: null
threat: null
component: null
---
During T-0154 land, the close CLI printed 'ERROR: close failed: MissingEvidence' yet exited 0, so a chained git commit ran and committed an unclosed ticket. A failed close MUST exit nonzero (vacuous-pass doctrine: a failure that reports success is the worst outcome). Audit all ticket_runner.py exit paths for the same print-error-return-zero pattern; add a CLI test asserting close on a ticket lacking evidence or a done report exits nonzero. Related: the same session saw sys audit print GAP lines but exit 0 once too -- sweep sys_runner.py and check_runner.py for the same class.