---
id: T-0102
title: frob check must FAIL, not silently pass, when the ticket queue fails to load
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/**
- src/frob/gates/**
- src/frob/tickets/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_check.py::TestRunGatesQueueFailure::test_malformed_tickets_md_is_hard_error_not_silent_skip
- tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_rejects_malformed_entry_before_write
- tests/test_tickets.py::TestEvidenceValidation::test_new_ticket_validates_evidence
designated_repro_test: null
threat: null
component: null
---
Found during T-0067/68 review: a malformed evidence block in tickets.md made load_queue fail; frob check printed 'gates skipped: Ticket queue failed to load' and EXITED 0 -- every obligation gate silently vanished while reporting success (the vacuous-pass class again). A queue load failure must be a hard error with remedy text. Companion fix: frob ticket new/close should validate evidence schema on write so malformed entries cannot land at all.