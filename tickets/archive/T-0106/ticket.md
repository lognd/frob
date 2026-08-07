---
id: T-0106
title: Wire frob ticket new/close --evidence to tickets.add_evidence
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
- docs/commands/check.md
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets_evidence_cli.py::TestTicketNewEvidence::test_resolvable_evidence_recorded_on_new_ticket
- tests/test_tickets_evidence_cli.py::TestTicketNewEvidence::test_unresolvable_evidence_does_not_abort_ticket_creation
- tests/test_tickets_evidence_cli.py::TestTicketNewEvidence::test_dedupes_against_already_recorded_evidence
- tests/test_tickets_evidence_cli.py::TestTicketCloseEvidence::test_resolvable_evidence_recorded_then_closed
- tests/test_tickets_evidence_cli.py::TestTicketCloseEvidence::test_unresolvable_evidence_blocks_close_entirely
- tests/test_tickets_evidence_cli.py::TestTicketCloseEvidence::test_dedupes_against_ids_already_on_ticket
designated_repro_test: null
threat: null
component: null
---
T-0102 added frob.tickets.validate_evidence/add_evidence but left them unwired from the new/close CLI (out of scope). MERGE NOTE: the standalone `frob ticket evidence` subcommand (T-0094) landed in parallel and covers the append-after-the-fact path; this ticket's remaining value is only the `--evidence` convenience flags on new/close. Re-evaluate scope before starting; drop if T-0094's surface suffices.