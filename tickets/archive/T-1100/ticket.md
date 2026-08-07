---
id: T-1100
title: 'frob ticket flow: created/day vs landed/day vs net + naive burn-down ETA (one
  table, builds on T-0938 velocity mining)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/__init__.py
- src/frob/app/ticket_runner.py
- tests/test_tickets_velocity.py
- docs/modules/tickets.md
- src/frob/_cli_parsers/_ticket.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_ticket.py
  reason: frob ticket flow needs CLI argparse/dispatch wiring and new report models
    outside the ticket's originally narrow scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: frob ticket flow needs CLI argparse/dispatch wiring and new report models
    outside the ticket's originally narrow scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: frob ticket flow needs CLI argparse/dispatch wiring and new report models
    outside the ticket's originally narrow scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/tickets/_models.py
  reason: frob ticket flow needs CLI argparse/dispatch wiring and new report models
    outside the ticket's originally narrow scope
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_tickets_velocity.py
  reason: frob ticket flow needs CLI argparse/dispatch wiring and new report models
    outside the ticket's originally narrow scope
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day
- tests/test_tickets_velocity.py::TestTicketFlow::test_zero_activity_days_are_filled_not_sparse
- tests/test_tickets_velocity.py::TestTicketFlow::test_eta_none_when_queue_not_shrinking
- tests/test_tickets_velocity.py::TestTicketFlow::test_eta_computed_when_queue_shrinking
designated_repro_test: null
acceptance:
- text: 'given a frob-enabled repo, when frob ticket flow runs, then it prints per-day
    filed/landed/net counts (created: fields + ledger git history via the T-0938 transition
    miner), current open count, the trailing-3-day net rate, and a naive ETA line
    (open / trailing net rate) clearly labeled as extrapolation'
  evidence:
  - tests/test_tickets_velocity.py::TestTicketFlow::test_filed_and_landed_counted_per_day
  - tests/test_tickets_velocity.py::TestTicketFlow::test_zero_activity_days_are_filled_not_sparse
  - tests/test_tickets_velocity.py::TestTicketFlow::test_eta_none_when_queue_not_shrinking
  - tests/test_tickets_velocity.py::TestTicketFlow::test_eta_computed_when_queue_shrinking
threat: null
component: null
---
User request 2026-07-28: a simple ticket data-analysis command showing the rate tickets grow vs the rate they complete. Reuse sprint_velocity's git-history transition mining (T-0938) for the landed side and the created: fields for the filed side; plain render-layer table, no new storage. Keep it genuinely simple -- one table plus one ETA line.