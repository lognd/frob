---
id: T-3061
title: Put the 2.9s lint gate back on the rapid land path without re-enabling TEST016
  mutation testing
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/check/_python.py
- src/frob/process/parsers/ruff.py
- docs/modules/tickets-landing.md
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: add lint gate to rapid land path (T-3061)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/check/_python.py
  reason: add lint gate to rapid land path (T-3061)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/process/parsers/ruff.py
  reason: add lint gate to rapid land path (T-3061)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: doc target for new pre-land lint gate function
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: evidence tests for new pre-land lint gate
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_lint_error_in_a_touched_file_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_a_clean_touched_file_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesLintCleanPreLand::test_empty_touched_set_is_a_no_op
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 7862fb4013cd6aaa2af121c6e9754fadfe9000ce
---
