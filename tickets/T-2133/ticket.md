---
id: T-2133
title: 'No pre-dispatch readiness check: a coordinator cannot see that a ticket is
  leased, already implemented on another branch, or scope-divergent without three
  hand-rolled git probes'
state: in-progress
kind: feature
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
evidence_scope:
- tests/unit/test_coordinator_scripts.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_coordinator_scripts.py
  reason: tests + doc anchors for the new fleet_status.py readiness functions
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/guides/coordinator-scripts.md
  reason: tests + doc anchors for the new fleet_status.py readiness functions
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_dispatchable_when_no_lease_no_commits_no_divergence
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_a_live_lease_exists
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_not_dispatchable_when_another_branch_already_has_commits
- tests/unit/test_coordinator_scripts.py::TestTicketReadiness::test_flags_scope_divergence_between_the_live_lease_and_main
- tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_ticket_flag_exits_one_when_not_dispatchable
- tests/unit/test_coordinator_scripts.py::TestFleetStatusMain::test_ticket_flag_exits_zero_when_dispatchable
- tests/unit/test_coordinator_scripts.py::TestTicketLease::test_reads_a_live_lease
- tests/unit/test_coordinator_scripts.py::TestTicketFrontmatterOnMain::test_reads_state_and_scope
- tests/unit/test_coordinator_scripts.py::TestWorktreesTouchingTicket::test_finds_a_branch_with_unlanded_commits
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
