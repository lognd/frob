---
id: T-2172
title: scripts/fleet_status.py::main crosses ARCH001/ARCH103 after T-2129/T-2133's
  land (230-line growth)
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- scripts/fleet_status.py
- tests/unit/test_coordinator_scripts.py
- docs/guides/coordinator-scripts.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: tests + doc anchors for the ARCH001/ARCH103 main() split
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: tests + doc anchors for the ARCH001/ARCH103 main() split
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_coordinator_scripts.py::TestPrintTicketReadiness::test_prints_dispatchable_true
- tests/unit/test_coordinator_scripts.py::TestPrintTicketReadiness::test_prints_lease_scope_divergence_and_sibling_commits
- tests/unit/test_coordinator_scripts.py::TestPrintFleetReport::test_prints_all_four_sections
- tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_ticket_readiness_prints_before_the_general_report
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2129/T-2133's land grew scripts/fleet_status.py by 230 lines, and its
`main()` crossed ARCH001 (78 lines, threshold 60) and ARCH103 (mixes I/O,
string-formatting, and 14 decision points in one body). These are
currently UNDISPOSED in the quarantine store and raising the verify
quarantine fleet-wide.

Fix: split `main()` into `_print_ticket_readiness(readiness) -> bool`
(the `TICKET <id>` block) and `_print_fleet_report(dirt, idle_seconds)
-> None` (the ROOT/QUARANTINE/LEASES/WORKTREES blocks), leaving `main`
itself as argument parsing plus the ordering/exit-code decision. Also
fixes the coordinator's own UX report: `--ticket T-####`'s readiness
block now prints FIRST, ahead of the general fleet report, instead of
being buried below it.