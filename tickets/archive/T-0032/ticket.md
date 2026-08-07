---
id: T-0032
title: 'Ticket schema: incident kind, acceptance, STRIDE threat, renumber'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- src/frob/app/config.py
- src/frob/__main__.py
- tests/test_tickets.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestSchemaExtras::test_renumber_makes_ids_contiguous
- tests/test_tickets.py::TestSchemaExtras::test_acceptance_and_threat_round_trip
designated_repro_test: null
threat: null
component: null
---
