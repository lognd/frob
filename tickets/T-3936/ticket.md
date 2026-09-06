---
id: T-3936
title: 'Windows CI: 19 remaining platform-specific failures (49 -> 28 -> 19 after
  shared causes removed)'
state: in-progress
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
scope_changes:
- op: remove
  glob: tests/unit/test_conftest_suite_result_status.py
  reason: these 3 files' Windows fixes are landing separately under T-4028 (a narrow
    carve-out of 6 of the 19 Windows failures, including the suite-abort hang) --
    narrowing T-3936's own scope to the remaining 15/19 (unblocks T-4028's start,
    which was refused on a scope-lease collision with this now-stale portion of T-3936's
    declared scope)
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/ticket_land_suite/test_land_lock.py
  reason: these 3 files' Windows fixes are landing separately under T-4028 (a narrow
    carve-out of 6 of the 19 Windows failures, including the suite-abort hang) --
    narrowing T-3936's own scope to the remaining 15/19 (unblocks T-4028's start,
    which was refused on a scope-lease collision with this now-stale portion of T-3936's
    declared scope)
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/test_tickets_mutation_evidence.py
  reason: these 3 files' Windows fixes are landing separately under T-4028 (a narrow
    carve-out of 6 of the 19 Windows failures, including the suite-abort hang) --
    narrowing T-3936's own scope to the remaining 15/19 (unblocks T-4028's start,
    which was refused on a scope-lease collision with this now-stale portion of T-3936's
    declared scope)
  actor: logan
  at: '2026-09-06'
body_changes:
- mode: set
  reason: 'first COMPLETE Windows run (34024645783) after the hang fix landed: 25
    failures out of 13468 with no incomplete marker. This supersedes the 49/28/21/19
    floors, none of which described a complete run. Recording the authoritative list,
    flagging that two of our own new Windows fixtures fail on real Windows, and separating
    the tzdata packaging cluster to T-4046'
  actor: logan
  at: '2026-09-06'
  old_length: 4025
  new_length: 9386
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
## THE FIRST COMPLETE MEASUREMENT: 25 FAILURES, run 34024645783 (78f511af0)

Until now every Windows number in this ticket was a FLOOR. The suite aborted
mid-run (FROB_TEST_HARD_EXIT killing an xdist worker), so the reported count was
"whatever ran before the abort" and the log said so explicitly: "failing set
INCOMPLETE -- run aborted before collecting/executing all tests". T-4028 landed
the hang fix, and this run reports:

    SUITE-RESULT: exitstatus=1 collected=13468 failed=25

with NO incomplete marker. THIS IS THE AUTHORITATIVE LIST. It supersedes the
earlier 49, 28, 21 and 19 figures, none of which described a complete run.

THE 25:
  tests/system/test_cli_ticket.py::TestTicketAttachNonInteractive::test_attach_without_path_fails_fast_off_tty
  tests/test_fuzz.py::TestRunFuzz::test_ungeneratable_target_reports_no_generator
  tests/test_telemetry.py::test_redundant_rerun_not_flagged_when_home_claude_config_changed
  tests/test_ticket_land_lint_diff_attribution.py::TestAssertTouchedFilesLintCleanPreLand::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse
  tests/test_ticket_leases.py::TestDispatchLandGuard::test_orphaned_squash_residue_is_reclaimed_before_a_mutating_verb_dispatches
  tests/test_tickets_evidence_cli.py::TestRunEvidenceCommandNoShell::test_shell_metacharacters_do_not_reach_a_shell
  tests/test_worktree_guard.py::TestAgentEnvStdoutPurity::test_bare_eval_succeeds_with_no_filtering
  tests/ticket_land_suite/test_land_core.py::TestRecordLandCommit::test_record_land_commit_never_absorbs_a_bystanders_dirty_file
  tests/ticket_land_suite/test_land_lock.py::TestLandLockHolderMetadataAndTimeout::test_orphaned_lock_from_a_confirmed_dead_pid_is_reclaimed_and_logged
  tests/ticket_land_suite/test_wip.py::TestWipCommitNormalizationOnlyDirty::test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed
  tests/unit/arch_suite/test_misc.py::TestCppSymrefCanonicalization::test_symref_matches_dsl_waiver_binding_exactly
  tests/unit/gates/test_exhaustive_handling_path_shape.py::test_windows_shaped_rel_path_mechanism
  tests/unit/gates/test_ffi_boundary_path_shape.py::test_windows_shaped_rel_path_mechanism
  tests/unit/rapid_sweep_suite/test_filing.py::TestRelativizeRegressionScopeFile::test_absolute_outside_root_is_kept_and_logged
  tests/unit/strata/test_strata_core_gil.py::TestTimeoutFiresDuringLongNativeCall::test_timeout_fires_during_worst_age
  tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline::test_missing_reason_is_not_silently_honored
  tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline::test_unrelated_files_waiver_does_not_suppress
  tests/unit/test_cycle_waiver.py::TestCycleWaiverPipeline::test_unwaived_cycle_reports
  tests/unit/test_dup.py::TestTestsDirectoryFloor::test_short_fixture_style_duplicate_under_tests_is_no_longer_a_group
  tests/unit/test_land_release_out_of_tree.py::TestApplyReleaseBumpOutOfTree::test_no_bump_returns_composed_commit_unchanged
  tests/unit/test_lang_primitives.py::test_symbol_tree_covers_span
  tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes
  tests/unit/test_reconcile_auto_commit_t1936.py::TestReconcileCommitScopedToLedgerRows::test_unrelated_dirty_file_is_not_swept_into_the_commit
  tests/unit/test_skills_sync.py::TestRun::test_run_defaults_to_home_claude_when_no_override_given
  tests/unit/test_sync_claude_config_stale_guard_t3408.py::TestStaleManagedSourcesAndWriteRefusal::test_stale_file_skipped_forward_file_synced

TWO OF THEM ARE OUR OWN NEW WINDOWS FIXTURES, AND THIS IS THE MOST IMPORTANT
ITEM IN THE LIST:

  tests/unit/gates/test_ffi_boundary_path_shape.py::test_windows_shaped_rel_path_mechanism
  tests/unit/gates/test_exhaustive_handling_path_shape.py::test_windows_shaped_rel_path_mechanism

These were added by T-3947/T-3948 to prove the backslash-path fixes, and were
verified on Linux by simulating Windows with PureWindowsPath. THEY FAIL ON REAL
WINDOWS. So the simulation and the platform disagree, which means the T-3947/
T-3948 fixes are NOT yet proven on the platform they were written for -- and
possibly not correct. TRIAGE THESE FIRST: a fixture that passes under simulation
and fails on the real platform is either testing the wrong thing or the fix is
wrong, and both outcomes matter more than the other 23. Note T-3941 (PROFILE001)
used the same simulation technique, so its fix is under the same doubt.

A CHEAP CLUSTER, ALREADY SEPARATED: `ModuleNotFoundError: No module named
'tzdata'` and `ZoneInfoNotFoundError: 'No time zone found with key UTC'` are a
missing platform-conditional dependency, filed as T-4046. Windows has no system
tz database. That is packaging, not Windows semantics -- do not debug it here.

VISIBLE CLUSTERS in the remainder, worth working as groups rather than 23
singletons: cycle_waiver (3, one file); the ~/.claude sync/telemetry trio
(skills_sync, sync_claude_config_stale_guard, telemetry redundant-rerun) which all
concern HOME-relative state and are likely one cause; the land/lock/wip git-
semantics group; and the stdout/TTY purity pair (worktree_guard, cli_ticket
attach off-tty) whose failure text is an explicit "assert 'TTY' in ..." mismatch.

STILL TRUE: no skip or xfail to reach green; a platform guard needs an explicit
condition whose reason states WHY in prose.
