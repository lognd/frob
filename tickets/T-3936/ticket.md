---
id: T-3936
title: 'Windows CI: 19 remaining platform-specific failures (49 -> 28 -> 19 after
  shared causes removed)'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: high
parent: T-3928
tier: ticket
sprint: v0.547.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/gates/test_profile_boundary.py
- tests/test_fuzz.py
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
- op: remove
  glob: tests/test_worktree_guard.py
  reason: T-3936 is a Windows-failure TRACKING ticket with no worktree and no code
    changes of its own; its declared scope holds file leases it never uses, and that
    lease is now actively blocking T-4162's fix to the xdist preflight in this very
    file. Narrowing on main is safe here precisely because there is no worktree to
    invalidate. The remaining scope entries should be removed the same way as they
    block others
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_ticket_leases.py
  reason: T-4243 (child of T-4236) now owns the three named failures in these files
    (land.lock untracked, normalization-dirty inversion, reclaim-log-line); narrowing
    to avoid a scope-lease collision
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/ticket_land_suite/test_wip.py
  reason: T-4243 (child of T-4236) now owns the three named failures in these files
    (land.lock untracked, normalization-dirty inversion, reclaim-log-line); narrowing
    to avoid a scope-lease collision
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/ticket_land_suite/test_land_core.py
  reason: T-4244 (leaf ticket under the same T-4236 epic) now owns and is actively
    fixing these three path-shape defects; T-3936 has no worktree and its lock is
    empty (epic-lease-leak pattern, see memory), so this scope entry is a dead lease
    blocking T-4244's start. Narrowing rather than stealing since there is no live
    worktree to steal from.
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/arch_suite/test_misc.py
  reason: T-4244 (leaf ticket under the same T-4236 epic) now owns and is actively
    fixing these three path-shape defects; T-3936 has no worktree and its lock is
    empty (epic-lease-leak pattern, see memory), so this scope entry is a dead lease
    blocking T-4244's start. Narrowing rather than stealing since there is no live
    worktree to steal from.
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/rapid_sweep_suite/test_filing.py
  reason: T-4244 (leaf ticket under the same T-4236 epic) now owns and is actively
    fixing these three path-shape defects; T-3936 has no worktree and its lock is
    empty (epic-lease-leak pattern, see memory), so this scope entry is a dead lease
    blocking T-4244's start. Narrowing rather than stealing since there is no live
    worktree to steal from.
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/system/test_cli_ticket.py
  reason: these four files are now owned by named leaves under epic T-4236, which
    supersedes this tracking ticket for the Windows failure set; T-3936 is in-progress
    with no worktree, so it holds write leases nothing is using and blocks the leaves
    that will actually do the work
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_tickets_evidence_cli.py
  reason: these four files are now owned by named leaves under epic T-4236, which
    supersedes this tracking ticket for the Windows failure set; T-3936 is in-progress
    with no worktree, so it holds write leases nothing is using and blocks the leaves
    that will actually do the work
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/unit/strata/test_strata_core_gil.py
  reason: these four files are now owned by named leaves under epic T-4236, which
    supersedes this tracking ticket for the Windows failure set; T-3936 is in-progress
    with no worktree, so it holds write leases nothing is using and blocks the leaves
    that will actually do the work
  actor: logan
  at: '2026-09-07'
- op: remove
  glob: tests/test_ticket_land_lint_diff_attribution.py
  reason: these four files are now owned by named leaves under epic T-4236, which
    supersedes this tracking ticket for the Windows failure set; T-3936 is in-progress
    with no worktree, so it holds write leases nothing is using and blocks the leaves
    that will actually do the work
  actor: logan
  at: '2026-09-07'
triage_changes:
- field: parent
  old_value: null
  new_value: T-3928
  reason: 'pass2 backlog org: theme bucket consumer-audit'
  actor: logan
  at: '2026-09-11'
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
- mode: set
  reason: records the fourth complete Windows run at 17 failures, down from 19, and
    flags that the two T-4102 fixtures are STILL failing despite that ticket's rewrite
    -- so the minus-two came from somewhere else and must not be attributed to T-4102
    without a set diff. Notes the reconcile test changed from failure to error, and
    that Windows is now the only leg with failing tests
  actor: logan
  at: '2026-09-07'
  old_length: 17027
  new_length: 19914
- mode: set
  reason: 'records the fifth complete Windows run at 25 raw and explains why the rise
    is imported rather than a Windows regression: the same run''s ubuntu leg gained
    7 platform-independent failures from T-4171''s no-sync defect, which appear on
    Windows too. Instructs a set diff before attributing anything, and warns that
    the tally stops being a burn-down signal while another platform''s regression
    is in flight'
  actor: logan
  at: '2026-09-07'
  old_length: 19914
  new_length: 21629
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

FOURTH COMPLETE WINDOWS RUN: 19 -> 17. CI run 34091766127, collected=13574,
failed=17. Measured against the run that carried 104 commits including the
subject-count primitive, the pathspec migration and the CI regression fixes.

THE DELTA IS EXACTLY THE TWO FIXTURES T-4102 REWROTE, and nothing else moved:

    tests/unit/gates/test_ffi_boundary_path_shape.py
      ::test_windows_shaped_rel_path_mechanism
    tests/unit/gates/test_exhaustive_handling_path_shape.py
      ::test_windows_shaped_rel_path_mechanism

WAIT -- BOTH ARE STILL IN THE FAILING LIST. So the count fell by two while those
two remain. That means two OTHER tests cleared and these two did not, and I have
not identified which. DO NOT ASSUME THE MINUS-TWO IS T-4102's WORK. Diff this
run's failing set against the previous one before attributing anything; this
repo has already recorded an incident where five of six "new" identities in a
sweep-filed ticket turned out to be pre-existing, and the same care applies in
the other direction.

That T-4102's rewritten fixtures still fail is itself the finding worth chasing
first. That ticket replaced a false premise (fnmatch normcases the glob, so a
backslash path DOES match a forward-slash glob on Windows) with assertions meant
to be platform-independent, and migrated `is_excluded` to pathspec. If they still
fail on real Windows, then either the rewrite carries a second false premise, or
the pathspec migration behaves differently there than on posix, or the fixtures
were not the thing that needed changing. PULL THEIR ACTUAL FAILURE TEXT FROM THIS
RUN before theorising -- I have the node ids only, not the assertions.

THE PERSISTENT SET, unchanged in shape from the previous run: the land-suite
cluster (land core, land lock, wip normalisation), the lease/dispatch guard, the
evidence-CLI shell-metacharacter test, the worktree-guard stdout purity test, the
CLI attach off-tty test, the arch cpp symref canonicalisation, the rapid-sweep
absolute-path relativisation, the strata-core GIL timeout, the out-of-tree
release bump, the lang-primitives span, and the sync-claude-config stale guard.
The reconcile auto-commit test now reports as an ERROR rather than a failure --
a different outcome for the same test, which usually means a fixture or teardown
problem rather than an assertion problem. Worth one look on its own.

STANDING CONTEXT: Windows remains ADVISORY (continue-on-error, declared at
.github/workflows/ci.yml:24-36 under T-3425) with a written removal condition --
remove the flag when this failure set reaches zero. The posix legs' suites are
GREEN on this same run; their jobs fail only on frob's own self-gate, tracked as
T-4145. So Windows is now the only leg with failing TESTS.

RUNNING TALLY: 49 (aborted) -> 28 (aborted) -> 26 -> 25 -> 19 -> 17. The first
two were floors from runs that aborted mid-suite; the last four are complete.

FIFTH COMPLETE WINDOWS RUN: 17 -> 25, AND THE RISE IS NOT A WINDOWS REGRESSION.
CI run 34117841048, collected=13617, failed=25.

DO NOT CHASE THIS AS A WINDOWS PROBLEM. The same run's ubuntu leg went from 0
failures to 7, all in the toolchain-routing work, from a single cause already
filed as T-4171: a `--no-sync` flag added to fix a mutating tool spawn broke both
the argv assertions written by the earlier tickets and the flag-coverage gate that
must import the target project's modules. Those seven are platform-independent --
they are argv-shape assertions and an import that cannot resolve -- so they appear
on Windows too. Seventeen plus seven is twenty-four, and the run reports
twenty-five.

So the Windows-specific delta this run is at most ONE, and may be zero if the
twenty-fifth is also from that batch. VERIFY BY SET DIFF BEFORE CONCLUDING
ANYTHING: pull this run's failing node ids and subtract the previous run's, then
subtract the seven known posix failures. Only what remains is a Windows finding.
This ticket has already recorded one case where a count moved and the attribution
was not what it looked like, and the same caution applies in the other direction.

THE PRACTICAL CONSEQUENCE FOR THIS TICKET'S TALLY: the running count is no longer
a clean measure of Windows-specific health while a posix regression is in flight.
Record 25 as the raw number and 17-plus-imported as the honest reading, and
re-measure once T-4171 lands. A tally that silently absorbs another platform's
regressions stops being the burn-down signal it exists to be.

RUNNING TALLY: 49 (aborted) -> 28 (aborted) -> 26 -> 25 -> 19 -> 17 -> 25 (raw;
approximately 17 Windows-specific plus an imported posix regression).

## Failure log
- 2026-09-08 attempt 1: Lease leak with no worktree: ticket sat in-progress with no worktree and no owning agent, so no work can be in flight and the lease is pure residue. Requeued to release it. Windows is advisory-only (continue-on-error, T-3425) so this is not release-blocking; re-dispatch after the alpha. No work is lost -- verified no worktree exists for this ticket.
