---
id: T-1163
title: 'fix: CLI_WIRING_FILES still points at retired src/frob/app/ticket_runner.py'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_models.py
- tests/test_tickets.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets.py
  reason: regression test for CLI_WIRING_FILES stale-path guard
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001: CLI_WIRING_FILES affects()-closure doc anchor must be touched'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_tickets.py::TestScopeMatching::test_cli_wiring_files_resolve_to_real_paths_on_disk
- tests/test_tickets.py::TestScopeMatching::test_feature_kind_implies_cli_wiring_files_in_scope
designated_repro_test: null
threat: null
component: null
---
Found while working T-1109 (DOC006 round-3 burn-down): frob.tickets._models.CLI_WIRING_FILES
(src/frob/tickets/_models.py ~line 204) still lists "src/frob/app/ticket_runner.py" as one of
the three always-in-scope CLI wiring files for a FEATURE ticket. That file was split into a
package (src/frob/app/ticket_runner/) by an earlier landing; the frozenset entry is now a
stale path that can never match a real file glob, silently defeating the T-0446 implicit-scope
mechanism for the ticket_runner half of CLI wiring on any FEATURE ticket.

Fix: update CLI_WIRING_FILES to the correct current path (e.g. a glob covering
src/frob/app/ticket_runner/**, or the package's __init__.py) and re-verify T-0446's own
tests still pass.