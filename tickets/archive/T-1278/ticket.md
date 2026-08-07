---
id: T-1278
title: 'TEST005 burn-down: src/frob/deploy (34 findings, 27 at 0.0%)'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/deploy/**
- tests/unit/deploy/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/deploy/**
  reason: actual test files live at tests/unit/deploy/**, not the placeholder tests/deploy/**
    path in the ticket body
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/unit/deploy/**
  reason: actual test files live at tests/unit/deploy/**, not the placeholder tests/deploy/**
    path in the ticket body
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/deploy/test_generate_windows.py::TestWindowsEntries::test_filters_to_windows_only
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_idempotent
- tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_when_bin_path_declared
- tests/unit/deploy/test_generate_windows.py::TestStatus::test_one_line
- tests/unit/deploy/test_generate_windows.py::TestUninstall::test_removes
- tests/unit/deploy/test_audit.py::TestDiff::test_no_diff
designated_repro_test: null
acceptance:
- text: GIVEN the deploy package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/deploy/**
  evidence:
  - tests/unit/deploy/test_generate_windows.py::TestWindowsEntries::test_filters_to_windows_only
  - tests/unit/deploy/test_generate_windows.py::TestInstall::test_idempotent
  - tests/unit/deploy/test_generate_windows.py::TestStatus::test_one_line
  - tests/unit/deploy/test_generate_windows.py::TestUninstall::test_removes
- text: GIVEN a 0.0%-branch symbol in deploy WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence:
  - tests/unit/deploy/test_audit.py::TestDiff::test_no_diff
- text: GIVEN a new test added to close a deploy TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/deploy/test_generate_windows.py::TestInstall::test_creates_service_when_bin_path_declared
threat: null
component: null
---
Package: src/frob/deploy (or the listed root modules).
TEST005 findings at current baseline: 34 total, 27 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_generate.py :: sorted_manifest_entries
_generate.py :: manifest_digest
_generate.py :: generate_install_script
_generate.py :: generate_status_script
_generate.py :: generate_uninstall_script
_generate.py :: generate_all
_drift.py :: deploy_drift_violations
_audit.py :: StateDiff.is_empty
_audit.py :: StateDiff.mutated_targets
_audit.py :: diff_states
_audit.py :: idempotence_holds
_audit.py :: artifact_freeness_holds
_audit.py :: install_exactness_holds
_audit.py :: assert_not_installed
_audit.py :: assert_healthy
_audit.py :: AuditAttestation.passed
_audit.py :: AuditAttestation.to_json
_audit.py :: build_attestation
_conform.py :: extract_mutation_surface
_conform.py :: expected_mutation_surface
_conform.py :: deploy_conformance_violations
_generate_windows.py :: windows_entries
_generate_windows.py :: generate_windows_install_script
_generate_windows.py :: generate_windows_status_script
_generate_windows.py :: generate_windows_uninstall_script
_vm_runner.py :: vboxmanage_available
_vm_runner.py :: run_vm_audit

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.