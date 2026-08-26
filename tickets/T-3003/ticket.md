---
id: T-3003
title: 'Windows now reaches the Test stage: 19 failures across 7 files, clustered
  in test_cli_check and test_rule_id_scan_branches'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_rule_id_scan.py
- tests/gates/test_rule_id_scan_branches.py
- src/frob/fleet/**
- tests/integration/test_fleet_integration.py
- tests/unit/test_land_squash_residue_reclaim.py
- src/frob/land/**
- tests/system/test_cli_check.py
- tests/system/test_cli_doctor.py
- tests/integration/test_interfaces.py
- tests/unit/strata/test_selfconform.py
- docs/modules/fleet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_rule_id_scan.py
  reason: 'T-3003 Windows pytest failure triage: fix path-separator and fcntl portability
    bugs; broad scope for cross-file investigation, will narrow to actual touched
    files at close'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/gates/test_rule_id_scan_branches.py
  reason: 'T-3003 Windows pytest failure triage: fix path-separator and fcntl portability
    bugs; broad scope for cross-file investigation, will narrow to actual touched
    files at close'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/fleet/**
  reason: 'T-3003 Windows pytest failure triage: fix path-separator and fcntl portability
    bugs; broad scope for cross-file investigation, will narrow to actual touched
    files at close'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/integration/test_fleet_integration.py
  reason: 'T-3003 Windows pytest failure triage: fix path-separator and fcntl portability
    bugs; broad scope for cross-file investigation, will narrow to actual touched
    files at close'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_land_squash_residue_reclaim.py
  reason: 'T-3003 Windows pytest failure triage: fix path-separator and fcntl portability
    bugs; broad scope for cross-file investigation, will narrow to actual touched
    files at close'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/land/**
  reason: 'T-3003 Windows pytest failure triage: fix path-separator and fcntl portability
    bugs; broad scope for cross-file investigation, will narrow to actual touched
    files at close'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/system/test_cli_check.py
  reason: 'T-3003 Windows pytest failure triage: fix path-separator and fcntl portability
    bugs; broad scope for cross-file investigation, will narrow to actual touched
    files at close'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: 'T-3003 Windows pytest failure triage: fix path-separator and fcntl portability
    bugs; broad scope for cross-file investigation, will narrow to actual touched
    files at close'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/integration/test_interfaces.py
  reason: 'T-3003 Windows pytest failure triage: fix path-separator and fcntl portability
    bugs; broad scope for cross-file investigation, will narrow to actual touched
    files at close'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: 'T-3003 Windows pytest failure triage: fix path-separator and fcntl portability
    bugs; broad scope for cross-file investigation, will narrow to actual touched
    files at close'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/fleet.md
  reason: close scope for fleet doc anchors surfaced by scope-closure warning
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
