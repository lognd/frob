---
id: T-0445
title: two more stale 'frob test --collect' references (ticket_runner.py:746, tickets/__init__.py:896)
  -- T-0292 sibling
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/__init__.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestEvidence::test_unresolvable_id_warning_names_no_nonexistent_flag
- tests/test_tickets_evidence_cli.py::TestLogEvidenceResultRemedy::test_error_remedy_names_no_nonexistent_flag
designated_repro_test: null
threat: null
component: null
---
