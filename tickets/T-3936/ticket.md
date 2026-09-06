---
id: T-3936
title: 'Windows CI: 19 remaining platform-specific failures (49 -> 28 -> 19 after
  shared causes removed)'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/gates/test_profile_boundary.py
- tests/ticket_land_suite/test_land_lock.py
- tests/test_tickets_mutation_evidence.py
- tests/unit/test_conftest_suite_result_status.py
- tests/unit/strata/test_strata_core_gil.py
- tests/unit/rapid_sweep_suite/test_filing.py
- tests/unit/arch_suite/test_misc.py
- tests/ticket_land_suite/test_wip.py
- tests/ticket_land_suite/test_land_core.py
- tests/test_worktree_guard.py
- tests/test_tickets_evidence_cli.py
- tests/test_ticket_leases.py
- tests/test_ticket_land_lint_diff_attribution.py
- tests/test_telemetry.py
- tests/test_fuzz.py
- tests/system/test_cli_ticket.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED, not inferred. CI run 34005559354 (28a511c9f) windows-latest: 28 SUITE-RESULT-FAILED. Six are T-3934 (target_branch, all platforms) and one is T-3935 (artifact-smoke, all platforms). The 19 below are genuinely Windows-specific and are the real remaining Windows number.

This supersedes the earlier inference that the prior round drained ~26 of 49. The measured drain was 49 -> 28.

THE 19 (verbatim node ids in $SCRATCH/win_remaining.txt):
  tests/system/test_cli_ticket.py::TestTicketAttachNonInteractive::test_attach_without_path_fails_fast_off_tty
  tests/test_fuzz.py::TestRunFuzz::test_ungeneratable_target_reports_no_generator
  tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed
  tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
  tests/test_ticket_leases.py::TestDispatchLandGuard::test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_dispatches
  tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_shell_metacharacters_do_not_reach_a_shell
  tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_already_landed_sibling_content_excluded
  tests/test_tickets_mutation_evidence.py::TestTouchedPythonFiles::test_matches_base_ref_tip_true_for_identical_content
  tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering
  tests/ticket_land_suite/test_land_core.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file
  tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout::test_holder_metadata_written_on_acquire
  tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged
  tests/ticket_land_suite/test_wip.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
  tests/unit/arch_suite/test_misc.py::TestCppSymrefCanonicalization::test_symref_matches_dsl_waiver_binding_exactly
  tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_positive_control_reintroduced_branch_is_flagged
  tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_pre_t2361_shape_is_flagged
  tests/unit/rapid_sweep_suite/test_filing.py::TestRelativizeRegressionScopeFile::test_absolute_outside_root_is_kept_and_logged
  tests/unit/strata/test_strata_core_gil.py::TestTimeoutFiresDuringLongNativeCall::test_timeout_fires_during_worst_age
  tests/unit/test_conftest_suite_result_status.py::TestSuiteResultDidNotComplete::test_sessionfinish_labels_did_not_complete_runs -- exceeded 600s timeout (thread-method os._exit, 1228.3s elapsed) -- not rescheduled (rerun cap 0 reached)

NOTE THE LAST ONE IS NOT AN ASSERTION FAILURE: test_conftest_suite_result_status exceeded the 600s timeout at 1228.3s under a thread-method os._exit. A hang is a different defect class from the other 18 and may be masking further failures behind it -- triage it FIRST and separately, because a run that dies at 1228s did not measure whatever came after it.

WORK IT IN CLUSTERS, not as 19 singletons. Visible groupings: land-lock/land-core/wip (git and lock semantics), mutation_evidence touched-file base-ref comparison, profile_boundary positive controls, and the stdout/tty purity pair (worktree_guard, cli_ticket attach off-tty).

DO NOT skip or xfail a Windows failure to reach green. An xfail here would be indistinguishable from a fix in the CI summary, which is the exact silent-zero shape this queue exists to prevent. If a case is genuinely not applicable on Windows, guard it with an explicit platform condition that states WHY in the skip reason.

ACCEPTANCE
- Each of the 19 either passes on Windows or carries a stated, reviewed platform guard.
- The hang is root-caused, not merely timed out differently.
- Re-measured on real Windows CI, not reasoned about.