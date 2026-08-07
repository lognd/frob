---
id: T-0579
title: 'frob ticket drop: first-class CLI for dropped-with-reason (today it is a hand-edit)'
state: done
kind: ux
origin: agent
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestDropTicket::test_drops_queued_ticket_with_reason
- tests/test_tickets.py::TestDropTicket::test_records_absorbed_by_reference
- tests/test_tickets.py::TestDropTicket::test_blank_reason_is_err
- tests/test_tickets.py::TestDropTicket::test_in_progress_ticket_drops_and_releases_lease
- tests/test_tickets.py::TestDropTicket::test_unknown_ticket_not_found
- tests/test_tickets.py::TestDropTicket::test_appends_preserving_existing_drop_reason_section
- tests/test_tickets.py::TestDropCli::test_cli_drops_with_reason
- tests/test_tickets.py::TestDropCli::test_cli_requires_reason
- tests/test_tickets.py::TestDropCli::test_cli_requires_id
designated_repro_test: null
threat: null
component: null
---
Dropping a ticket (absorbed elsewhere, obsolete, subsumed) required hand-editing state: dropped ~6 times this session because close demands evidence and no drop command exists. Add frob ticket drop <id> --reason TEXT [--absorbed-by T-####] writing the dated reason line, releasing leases, TICK-gate clean. Scope: src/frob/tickets/, app/ticket_runner.py, docs.