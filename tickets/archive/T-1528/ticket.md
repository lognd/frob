---
id: T-1528
title: 'frob ticket list: one-line state summary footer + --stats velocity/ETA line'
state: done
kind: ux
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/modules/tickets.md
- src/frob/app/ticket_runner/_query.py
- src/frob/tickets/_setters.py
- src/frob/tickets/_models.py
- src/frob/app/config.py
- src/frob/app/_config_external.py
- src/frob/_cli_parsers/_ticket/_query.py
- tests/unit/test_ticket_list_summary.py
- tests/test_tickets_velocity.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/tickets.md
  reason: TicketFlowReport median_cycle_days + list footer documented (AFFECT001 obligation)
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/app/ticket_runner/_query.py
  reason: T-1528 summary footer + stats implementation surface
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/tickets/_setters.py
  reason: T-1528 summary footer + stats implementation surface
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/tickets/_models.py
  reason: T-1528 summary footer + stats implementation surface
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/app/config.py
  reason: T-1528 summary footer + stats implementation surface
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/app/_config_external.py
  reason: T-1528 summary footer + stats implementation surface
  actor: logan
  at: '2026-08-04'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_query.py
  reason: T-1528 summary footer + stats implementation surface
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/unit/test_ticket_list_summary.py
  reason: T-1528 summary footer + stats implementation surface
  actor: logan
  at: '2026-08-04'
- op: add
  glob: tests/test_tickets_velocity.py
  reason: T-1528 summary footer + stats implementation surface
  actor: logan
  at: '2026-08-04'
evidence:
- tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_counts_per_state
- tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_empty_queue
- tests/unit/test_ticket_list_summary.py::TestStatsLine::test_renders_rates_cycle_and_eta
- tests/unit/test_ticket_list_summary.py::TestStatsLine::test_labels_unshrinking_and_missing_cycle
- tests/unit/test_ticket_list_summary.py::TestListFooterEndToEnd::test_list_always_prints_summary
- tests/test_tickets_velocity.py::TestTicketFlow::test_median_cycle_days_from_created_to_first_done
designated_repro_test: null
acceptance:
- text: GIVEN frob ticket list runs (any filter, empty or not) THEN a single summary
    footer line reports the total active count and per-state counts with zero extra
    IO, and GIVEN --stats THEN a second line reports trailing filed/landed/net per-day
    rates, median created-to-done cycle days (n/a when nothing completed), and the
    naive backlog ETA (labeled not-shrinking when net is non-negative)
  evidence:
  - tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_counts_per_state
  - tests/unit/test_ticket_list_summary.py::TestSummaryFooter::test_empty_queue
  - tests/unit/test_ticket_list_summary.py::TestStatsLine::test_renders_rates_cycle_and_eta
  - tests/unit/test_ticket_list_summary.py::TestStatsLine::test_labels_unshrinking_and_missing_cycle
  - tests/unit/test_ticket_list_summary.py::TestListFooterEndToEnd::test_list_always_prints_summary
  - tests/test_tickets_velocity.py::TestTicketFlow::test_median_cycle_days_from_created_to_first_done
threat: null
component: null
---
Coordinators keep running 'frob ticket list | grep queued | wc -l' for basic queue telemetry. Add (1) an always-on single summary footer to frob ticket list: counts per state (queued/planned/in-progress/blocked/done-unarchived/dropped-unarchived) computed from the already-loaded queue -- zero extra IO; (2) a --stats flag appending a second line with historic velocity reusing the existing T-1100/T-0938 flow machinery: median cycle time (created->done), landed/day and filed/day over the trailing window, net burn rate, and a naive backlog ETA (queued / net-landed-per-day, 'growing' when net is negative). Requested by user 2026-08-04.