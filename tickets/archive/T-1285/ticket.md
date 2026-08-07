---
id: T-1285
title: 'TEST005 burn-down: src/frob/fleet (5 findings, 4 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/fleet/**
- tests/fleet/**
- tests/unit/fleet/**
- docs/modules/fleet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/fleet/**
  reason: tests actually live under tests/unit/fleet, and fleet symbols' frob:doc
    targets point at docs/modules/fleet.md
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/fleet.md
  reason: tests actually live under tests/unit/fleet, and fleet symbols' frob:doc
    targets point at docs/modules/fleet.md
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/fleet/test_manifest.py::TestLoadManifest::test_load_manifest_schema_invalid
- tests/unit/fleet/test_status.py::TestCollectStatus::test_git_branch_and_dirty_subprocess_raises
- tests/unit/fleet/test_status.py::TestCollectStatus::test_git_branch_and_dirty_clean_tree_stays_not_dirty
- tests/unit/fleet/test_status.py::TestCollectStatus::test_gate_summary_probe_subprocess_raises
- tests/unit/fleet/test_status.py::TestCollectStatus::test_gate_summary_probe_non_json_output
- tests/unit/fleet/test_status.py::TestCollectStatus::test_count_diagnostics_ignores_unknown_severities
- tests/unit/fleet/test_status.py::TestCollectStatus::test_doable_count_missing_ledger_returns_zero
- tests/unit/fleet/test_status.py::TestCollectStatus::test_doable_count_delegates_to_tickets_api
- tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_new_ticket_failure_wrapped
designated_repro_test: null
acceptance:
- text: GIVEN the fleet package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/fleet/**
  evidence:
  - tests/unit/fleet/test_manifest.py::TestLoadManifest::test_load_manifest_schema_invalid
  - tests/unit/fleet/test_status.py::TestCollectStatus::test_git_branch_and_dirty_subprocess_raises
  - tests/unit/fleet/test_status.py::TestCollectStatus::test_git_branch_and_dirty_clean_tree_stays_not_dirty
  - tests/unit/fleet/test_status.py::TestCollectStatus::test_gate_summary_probe_subprocess_raises
  - tests/unit/fleet/test_status.py::TestCollectStatus::test_gate_summary_probe_non_json_output
  - tests/unit/fleet/test_status.py::TestCollectStatus::test_count_diagnostics_ignores_unknown_severities
  - tests/unit/fleet/test_status.py::TestCollectStatus::test_doable_count_missing_ledger_returns_zero
  - tests/unit/fleet/test_status.py::TestCollectStatus::test_doable_count_delegates_to_tickets_api
- text: GIVEN a 0.0%-branch symbol in fleet WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_new_ticket_failure_wrapped
- text: GIVEN a new test added to close a fleet TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/fleet/test_route.py::TestRouteTicket::test_route_ticket_new_ticket_failure_wrapped
threat: null
component: null
---
Package: src/frob/fleet (or the listed root modules).
TEST005 findings at current baseline: 5 total, 4 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
__init__.py :: load_manifest
__init__.py :: collect_status
__init__.py :: rollup
__init__.py :: route_ticket

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.