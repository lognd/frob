---
id: T-1570
title: 'cli regrouping: resolve ticket/debt/deprecated naming (frob tickets vs frob
  ticket)'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: medium
blocked_by:
- T-1725
- T-1764
- T-1765
- T-1766
parent: T-1238
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/_cli_parsers/_reporting.py
- src/frob/_cli_parsers/_ticket/__init__.py
- src/frob/app/ticket_runner/__init__.py
- docs/design/cli-regrouping.md
- docs/modules/cli.md
- tests/unit/test_app_runners_batch7.py
- tickets/T-1570/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: narrow mega-glob to the exact files T-1570 (ticket/debt/deprecated naming
    resolution) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: narrow mega-glob to the exact files T-1570 (ticket/debt/deprecated naming
    resolution) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: narrow mega-glob to the exact files T-1570 (ticket/debt/deprecated naming
    resolution) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/cli-regrouping.md
  reason: narrow mega-glob to the exact files T-1570 (ticket/debt/deprecated naming
    resolution) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/cli.md
  reason: narrow mega-glob to the exact files T-1570 (ticket/debt/deprecated naming
    resolution) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: narrow mega-glob to the exact files T-1570 (ticket/debt/deprecated naming
    resolution) touches
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1570/**
  reason: narrow mega-glob to the exact files T-1570 (ticket/debt/deprecated naming
    resolution) touches
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_debt_subcommand_delegates_to_debt_runner
- tests/unit/test_app_runners_batch7.py::TestTicketRunnerDispatch::test_deprecated_subcommand_delegates_to_deprecated_runner
designated_repro_test: null
threat: null
component: null
---
Refiled from T-1570 (T-1238 naming-decision slice, draft-loss class). Decide and implement the singular/plural verb naming for ticket/debt/deprecated surfaces as part of the T-1238 regroup.