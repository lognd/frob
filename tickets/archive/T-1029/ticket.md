---
id: T-1029
title: 'ticket CLI: add acceptance criteria to an existing ticket (only ticket new
  supports --acceptance)'
state: done
kind: ux
origin: agent
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- src/frob/tickets/
- tests/unit/test_ticket_runner_gate_findings.py
- docs/modules/tickets.md
- src/frob/_cli_parsers/_ticket.py
- src/frob/app/config.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_mutate.py
- tests/test_tickets.py
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: new 'frob ticket accept' CLI surface needs argparse wiring, AppConfig fields,
    dispatch-table registration, and doc anchors outside the ticket's original narrow
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/_cli_parsers/_ticket.py
  reason: new 'frob ticket accept' CLI surface needs argparse wiring, AppConfig fields,
    dispatch-table registration, and doc anchors outside the ticket's original narrow
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/config.py
  reason: new 'frob ticket accept' CLI surface needs argparse wiring, AppConfig fields,
    dispatch-table registration, and doc anchors outside the ticket's original narrow
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: new 'frob ticket accept' CLI surface needs argparse wiring, AppConfig fields,
    dispatch-table registration, and doc anchors outside the ticket's original narrow
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: new 'frob ticket accept' CLI surface needs argparse wiring, AppConfig fields,
    dispatch-table registration, and doc anchors outside the ticket's original narrow
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets.py
  reason: new 'frob ticket accept' CLI surface needs argparse wiring, AppConfig fields,
    dispatch-table registration, and doc anchors outside the ticket's original narrow
    scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/app.md
  reason: new 'frob ticket accept' CLI surface needs argparse wiring, AppConfig fields,
    dispatch-table registration, and doc anchors outside the ticket's original narrow
    scope
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets.py::TestAddAcceptance::test_appends_criteria_to_existing_ticket
- tests/test_tickets.py::TestAddAcceptance::test_empty_criteria_is_rejected
- tests/test_tickets.py::TestAddAcceptance::test_blank_criteria_are_dropped
designated_repro_test: null
acceptance:
- text: GIVEN an existing queued ticket WHEN the new subcommand adds a criterion THEN
    ticket show displays it and the ledger write went through the CLI
  evidence:
  - tests/test_tickets.py::TestAddAcceptance::test_appends_criteria_to_existing_ticket
  - tests/test_tickets.py::TestAddAcceptance::test_empty_criteria_is_rejected
  - tests/test_tickets.py::TestAddAcceptance::test_blank_criteria_are_dropped
threat: null
component: null
---
T-0894's agent had to hand-edit tickets.md to add a before-fails/after-passes acceptance criterion required by the T-0756 new-gate-rule close gate, because no subcommand exists to append acceptance criteria to an existing ticket. Add e.g. 'frob ticket accept <id> --criterion ...' (or extend ticket scope-style editing) with the same validation as ticket new --acceptance, so the ledger is never hand-edited for this.