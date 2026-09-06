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
- op: remove
  glob: tests/test_telemetry.py
  reason: 'narrowed: tests/test_telemetry.py''s HOME-relative fixture bug is now owned
    by T-4057 (Cluster B)'
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
- mode: set
  reason: full per-failure tracebacks obtained from a complete Windows run; classifying
    the 26 into six mechanism clusters with a suggested order. Notably cluster C is
    a dead cycle detector (a subject-count/positive-control instance, not three test
    bugs) and two of cluster A are our own fixtures encoding a false premise
  actor: logan
  at: '2026-09-06'
  old_length: 9386
  new_length: 13772
- mode: set
  reason: 'third complete Windows run: 26 -> 19 with cluster C (cycle detector) entirely
    cleared including its positive control, and two of the HOME cluster. Records one
    NEW failure (gate cache serving a stale hit after a tracked-file edit) and verifies
    it is not from T-3985, which landed after this commit'
  actor: logan
  at: '2026-09-06'
  old_length: 13772
  new_length: 17027
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

## FULL TRACEBACKS OBTAINED: THE 26 CLASSIFIED BY MECHANISM

A later complete run (26 failures, collected=13473) returned per-failure
tracebacks. The list is stable between runs -- the same tests fail -- so unlike
ubuntu this is a fixed defect set, not a flake population. WORK THESE AS SIX
CLUSTERS, not 26 singletons.

CLUSTER A -- PATH SEPARATOR SEMANTICS (7). The dominant cluster.
  arch_suite/test_misc::test_symref_matches_dsl_waiver_binding_exactly
      'C:\...\long.cpp::Foo.bar' != 'C:/...' -- a symref built with backslashes
      compared against one built with forward slashes. THE SAME PRODUCER/
      VALIDATOR SPLIT as T-3941; likely a genuine defect.
  ticket_land_suite/test_land_core::..._never_absorbs_a_bystanders_dirty_file
      'tickets\T-3000\ticket.md' not found in git's output 'tickets/T-3000/...'
      -- GIT ALWAYS EMITS FORWARD SLASHES; the test builds the needle with
      WindowsPath. Test-side defect.
  unit/test_dup::test_short_fixture_style_duplicate_under_tests_is_no_longer_a_group
      CodeFragment(file='tests\\test_one.py') -- the tests/ floor glob does not
      match backslash paths. PRODUCTION-side; check whether the floor uses
      fnmatch (platform-dependent, see below) or startswith.
  unit/rapid_sweep_suite/test_filing::test_absolute_outside_root_is_kept_and_logged
      backslash-escaping in the logged message vs the expected literal.
  unit/gates/test_ffi_boundary_path_shape + test_exhaustive_handling_path_shape
      OUR OWN NEW FIXTURES, and they encode a FALSE PREMISE -- see the correction
      recorded on T-3947/T-3948: is_excluded returns True on Windows because
      fnmatch normcases the GLOB's forward slashes to backslashes. FIX OR DELETE
      THESE FIRST; they currently assert Windows behaves as Linux.
  unit/test_lang_primitives::test_symbol_tree_covers_span
      'def ' missing from the front and a trailing newline present -- a span/
      offset computed over CRLF text. Byte-offset vs character-offset.

CLUSTER B -- HOME-RELATIVE STATE (3).
  test_telemetry::test_redundant_rerun_not_flagged_when_home_claude_config_changed
  unit/test_skills_sync::test_run_defaults_to_home_claude_when_no_override_given
  unit/test_sync_claude_config_stale_guard_t3408::test_stale_file_skipped_forward_file_synced
      All three concern ~/.claude. On Windows HOME is not the same concept
      (USERPROFILE/APPDATA), so a fake-home fixture that works on posix does not
      redirect the code under test. Likely ONE root cause for all three.

CLUSTER C -- CYCLE DETECTION RETURNS NOTHING (3).
  unit/test_cycle_waiver:: all three cases report 'no cycles', exit 0, empty
  diagnostics -- including the UNWAIVED positive control. So frob-cycle finds no
  cycles at all on Windows. THIS IS A SUBJECT-COUNT INSTANCE and a positive
  control correctly reporting a dead detector -- treat it like PROFILE001
  (T-3941), not like three test bugs. HIGH PRIORITY: a detector that silently
  finds nothing is the class this queue exists to catch.

CLUSTER D -- GIT AND PROCESS ENVIRONMENT (4).
  unit/test_process_lock (x3): `git config user.email` RETURNS 130, and a
      BrokenProcessPool. Exit 130 is SIGINT-shaped -- something is killing git.
      Investigate as one cause; 130 from `git config` is not a normal failure.
  ticket_land_suite/test_land_lock::..._orphaned_lock_..._reclaimed_and_logged
      no reclaim log lines -- pairs with the known Windows mandatory-locking
      issue already filed as T-4029.

CLUSTER E -- ENCODING (1), and it is the most diagnostic single failure.
  test_worktree_guard::test_bare_eval_succeeds_with_no_filtering
      stdout contains '\x00s\x00t\x00r\x00o\x00' -- that is UTF-16LE. A Windows
      shell is emitting UTF-16 where the test expects UTF-8. Worth fixing early:
      any other test asserting on captured output could be affected the same way.

CLUSTER F -- SINGLETONS (8): tzdata (already T-4046), the TTY assertion in
  cli_ticket attach, land_lint_diff_attribution SystemExit, ticket_leases
  '?? .frob/land.lock' untracked, test_wip git status empty when non-empty
  expected (autocrlf), strata_core_gil timeout marker absent,
  land_release_out_of_tree sha mismatch, tickets_evidence_cli EvidenceCmdFailed.

SUGGESTED ORDER: C (dead detector) -> A's two false fixtures -> B (one cause, 3
tests) -> E (encoding, may unblock others) -> D -> A's remainder -> F.

## MEASURED DELTA ON cc3dae236: 26 -> 19, WITH WHOLE CLUSTERS CLEARED

Third complete Windows run (collected=13494, failed=19). macOS PASSED on the same
commit -- the first fully green leg of this drive -- and ubuntu was still running.

CLEARED SINCE THE 26-FAILURE RUN, and each confirms a landed fix on real Windows
rather than by simulation:
  - test_cycle_waiver x3  -> T-4056 (the dead cycle detector). The whole of
    cluster C is gone, INCLUDING the unwaived positive control. That is the
    strongest confirmation available: the detector now finds the cycle it was
    blind to.
  - test_telemetry, test_skills_sync -> T-4057's Path.home fixture fix. Two of
    that cluster's three.
  - test_process_lock x3 (the `git config` exit-130 and BrokenProcessPool cases)
    and test_reconcile_auto_commit -> cleared without a targeted fix; likely
    downstream of the same environment work, but NOT attributable with
    confidence. Do not claim them.

STILL FAILING AND EXPECTED TO:
  - The two path-shape fixtures (ffi_boundary, exhaustive_handling) fail with the
    SAME assertion as before -- `is_excluded('vendor\sub\mod.py', ('vendor/**',))`
    returns True. That is the false premise recorded on T-3947/T-3948: fnmatch
    normcases the GLOB's forward slashes to backslashes on Windows, so the match
    SUCCEEDS and the fixtures assert the opposite. REWRITE OR DELETE THEM; they
    are two of the 19 and neither represents a real defect.
  - test_sync_claude_config_stale_guard: T-4057's CRLF production fix did NOT
    resolve it on real Windows. That agent explicitly caveated the fix rested on
    documented git/ntpath semantics rather than a measurement -- the caveat was
    right. Re-open that mechanism rather than assuming the fix is merely
    incomplete.
  - tzdata (test_fuzz) is back, with the same ZoneInfoNotFoundError. It was absent
    from the previous run purely because hypothesis did not generate the case --
    confirming the earlier note that its absence was luck, not resolution.
    T-4046 remains unfixed.

ONE NEW FAILURE, NOT PRESENT IN THE 26-RUN:
    tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates
    ::test_tracked_file_edit_forces_process_gate_recompute
    "a tracked-file edit must force a real archgate re-run, not a stale cache
     hit" -- assert 0.0 != 0.0

I CHECKED WHETHER THIS IS OURS AND IT IS NOT T-3985: that ticket wired
subject-count probes into `src/frob/check/_python.py` (the gate pipeline, exactly
where a cache regression would live), but it landed AFTER this commit and is still
unpushed -- `git merge-base --is-ancestor 79200c119 cc3dae236` is false. The
assertion itself dates to T-1445's gate-result cache work.

So it is either a genuine Windows cache defect (mtime resolution or cache keying
differing on NTFS is the obvious candidate) or a new flake. TREAT IT AS THE FIRST
UNTIL MEASURED: an archgate timing of exactly 0.0 means the gate did not run at
all, which is a stale-cache hit -- and a cache that serves stale results after a
tracked-file edit is a silent-zero shape, not a timing wobble.

RUNNING TALLY: 49 (aborted) -> 28 (aborted) -> 26 -> 25 -> 19. The first three
were floors from runs that aborted mid-suite; only the last three are complete
counts.
