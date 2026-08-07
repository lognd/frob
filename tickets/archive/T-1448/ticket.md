---
id: T-1448
title: 'main suite red: 14 failures after the 2026-08-02 wave-2/3 lands'
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- tests/test_ticket_land.py
- tests/unit/test_app_runners_t0976_mutation_evidence.py
- tests/unit/test_ticket_close_gate_claims_t1410.py
- tests/unit/test_ticket_close_own_obligations_t1387.py
- tests/unit/test_extending_guides_complete.py
- docs/guides/extending/**
- tests/unit/strata/test_selfconform.py
- tests/system/test_cli_native_missing.py
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: need --dist=loadgroup for xdist_group serialization fix on the two full-repo-scan
    tests (cluster 3)
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade::test_true_mutation_evidence_with_skip_flag_is_never_downgraded
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade::test_false_mutation_evidence_with_skip_flag_is_downgraded_to_none
- tests/unit/test_app_runners_t0976_mutation_evidence.py::TestCloseGuardsMutationEvidenceDowngrade::test_false_mutation_evidence_without_skip_flag_stays_false
- tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseRefusesT1276ShapeEndToEnd::test_close_refuses_when_live_findings_remain_under_the_glob
- tests/unit/test_ticket_close_gate_claims_t1410.py::TestCloseRefusesT1276ShapeEndToEnd::test_close_succeeds_once_the_glob_is_actually_clean
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseRefusesOwnObligationsEndToEnd::test_close_refuses_when_own_diff_leaves_cov001_outstanding
- tests/unit/test_ticket_close_own_obligations_t1387.py::TestCloseRefusesOwnObligationsEndToEnd::test_close_succeeds_once_the_diff_is_actually_clean
- tests/test_ticket_land.py::TestCloseSkipMutationEvidenceBypass::test_skip_flag_bypasses_error_verdict
- tests/test_ticket_land.py::TestCloseSkipMutationEvidenceBypass::test_no_skip_flag_refuses_on_error_verdict
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_probe_still_matches_source
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_row_anchor_file_exists_and_mentions_guide
- tests/unit/test_extending_guides_complete.py::TestExtendingGuidesComplete::test_every_anchor_fragment_resolves_to_guide_h1
- tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
- tests/system/test_cli_native_missing.py::TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files
designated_repro_test: null
threat: null
component: null
---
14 tests are failing on main (make coverage, 2026-08-02 14:19 run, log at
.frob/last-coverage-run.log) after the wave-2/wave-3 lands that day.
Clustered by likely root cause:

1. Close-path cluster (9 tests): tests/test_ticket_land.py::
   TestCloseSkipMutationEvidenceBypass (2), tests/unit/
   test_app_runners_t0976_mutation_evidence.py::
   TestCloseGuardsMutationEvidenceDowngrade (3), tests/unit/
   test_ticket_close_gate_claims_t1410.py (2), tests/unit/
   test_ticket_close_own_obligations_t1387.py (2). T-1438 changed
   _close_mutation_evidence_for_ticket (src/frob/app/ticket_runner/
   _close_cmd.py) to resolve the repro base via git merge-base instead of
   current_branch; these tests' fixtures likely assume the old call shape
   or run in non-git tmp dirs. Must preserve T-1438's behavior (verified
   by tests/unit/test_ticket_close_bug002_t1438.py, which passes).

2. Extending-guides cluster (3): tests/unit/
   test_extending_guides_complete.py -- doc anchor/probe assertions
   against source that T-1420's splits relocated (_threat.py ->
   _threat_* modules, _capability_registry.py -> package). Repoint the
   guide anchors/probes in docs/guides/extending/** to the new homes.

3. tests/unit/strata/test_selfconform.py::TestCoverageTotality::
   test_repo_unrestricted_scan_is_clean -- also crashed an xdist worker
   (gw1) in one run. Diagnose memory footprint of the unrestricted repo
   capability scan or mark serial with a recorded reason.

4. tests/system/test_cli_native_missing.py::
   TestNativeMissingFailsLoud::test_check_unaffected_when_no_strata_files
   -- likely env-shape assumption; diagnose honestly.

Fix all 14, in worktree/branch w4j-suite cut from main.