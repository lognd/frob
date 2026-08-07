---
id: T-0826
title: 'tickets CLI: done-report --why-file duplicates the ''## Done report'' heading
  (recurring cosmetic ledger noise)'
state: done
kind: ux
origin: agent
created: '2026-07-23'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_store.py::TestComposeDoneReport::test_strips_duplicate_leading_heading_from_why
- tests/unit/test_ticket_store.py::TestComposeDoneReport::test_composes_all_three_sections
designated_repro_test: null
acceptance:
- text: GIVEN a why-file that already begins with a Done report heading WHEN frob
    ticket done-report renders it THEN exactly one heading appears in the ledger block;
    existing double-heading blocks are tolerated by parsers
  evidence:
  - tests/unit/test_ticket_store.py::TestComposeDoneReport::test_strips_duplicate_leading_heading_from_why
  - tests/unit/test_ticket_store.py::TestComposeDoneReport::test_composes_all_three_sections
threat: null
component: null
---
Recurred 5+ times this drive (reviewers keep flagging it cosmetically): done-report prepends its own heading on top of one already present in --why-file content. Deduplicate at render time.