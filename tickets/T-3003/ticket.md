---
id: T-3003
title: 'Windows now reaches the Test stage: 19 failures across 7 files, clustered
  in test_cli_check and test_rule_id_scan_branches'
state: done
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
- src/frob/mutate/_journal.py
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
- op: add
  glob: src/frob/mutate/_journal.py
  reason: windows os.kill(pid,0) liveness-probe fix for the mutate-journal doctor
    check (real portability+safety defect found during T-3003 triage)
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/system/test_cli_doctor.py
  reason: windows os.kill(pid,0) liveness-probe fix for the mutate-journal doctor
    check (real portability+safety defect found during T-3003 triage)
  actor: logan
  at: '2026-08-26'
body_changes:
- mode: append
  reason: 'waive BUG002: Windows-only defect, no local reproduction possible'
  actor: logan
  at: '2026-08-26'
  old_length: 0
  new_length: 696
evidence:
- tests/gates/test_rule_id_scan_branches.py::TestScanEmittedRuleIdsBranches::test_const_ref_resolves_against_assignment_in_another_file
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_typed_const_assignment
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_bare_positional_argument
- tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_code_kwarg_outside_scanned_bases
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_reports_a_candidate_missing_from_both_known_and_retired
- tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_disclosed_gap_shape_still_requires_hand_registration
- tests/integration/test_fleet_integration.py::TestFleetIntegration::test_fleet_status_table_over_real_repos
- tests/integration/test_fleet_integration.py::TestFleetIntegrationJson::test_fleet_status_json_is_clean
- tests/integration/test_interfaces.py::TestInterfaces::test_cycle_cli
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging
- tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_unhealthy_with_stale_mutate_journal
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive BUG002 reason="T-3003 fixes Windows-only portability defects (path-separator stringification in _rule_id_scan.py, os.kill(pid,0) able to TerminateProcess on Windows in mutate/_journal.py) that cannot be reproduced by any test run on this Linux CI/dev environment -- the defects only manifest on a real windows-latest runner (verified via the actual job log, run 32990187048/job 98245674275). The bound evidence node ids pass at both main and the fix on Linux by construction; the fixes were verified against the fcntl/msvcrt/os.kill semantics documented in each platform's own stdlib behavior and against the exact failure text from the real Windows CI job log, not by a local repro."