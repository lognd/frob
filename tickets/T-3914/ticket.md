---
id: T-3914
title: 'win32: classify and drain the current 49-failure set (post T-3797), split
  test-harness vs real defects'
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_conftest_suite_result_status.py
- tests/unit/test_draft_finalize_attachments.py
- tests/unit/test_ticket_new_body_file_pipe_t2021.py
- src/frob/app/ticket_runner/_new.py
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
Filed under T-3505 (Windows portability epic). The most recent isolated
windows-only CI run (33948799774, job 101259585024, HEAD includes T-3797's
guarded_subprocess_run WinError2 fix) shows:

    SUITE-RESULT: exitstatus=1 collected=13352 failed=49

This is a stable, completed (non-interrupted) run -- the T-3511/T-3540
KeyboardInterrupt blocker and the T-3797 doctor-cluster (WinError 2) are
both resolved; this is the real remaining denominator.

Classification of the 49 (via -rA --tb=short full tracebacks, T-3785):

(a) TEST-HARNESS POSIX ASSUMPTIONS (test embeds a POSIX-only shape; the
    product is fine or the assertion literal is wrong for win32) --
    roughly 26 of 49, including:
  - tests/unit/test_conftest_suite_result_status.py (8): fake
    session/config test doubles (_FakeSession, _FakeConfigureConfig)
    lack .exitstatus / .pluginmanager attrs that tests/conftest.py's
    real hard-exit path reads unconditionally -- fixture gap, not a
    platform defect.
  - tests/unit/test_draft_finalize_attachments.py (2): the test helper
    _seed_draft_with_attachment builds Attachment.path via
    str(p.relative_to(root)) instead of .as_posix() -- the TEST fixture
    leaks a native separator; product's own posix-shape contract (see
    src/frob/tickets/_reporting_attachments.py's own as_posix() call)
    is untouched.
  - tests/unit/test_ticket_new_body_file_pipe_t2021.py (2): uses
    /dev/fd/N FIFO reads, a POSIX-only mechanism with no win32
    equivalent.
  - tests/test_testing.py::test_cargo_env_ok_when_python311_and_libdir_found:
    asserts LD_LIBRARY_PATH (POSIX dynamic-loader var; win32's
    analogous mechanism is PATH, not this key).
  - tests/test_testing.py::test_single_file_extension_fingerprinted:
    hardcodes a .so filename; win32 extension modules are .pyd.
  - tests/test_fuzz.py::test_ungeneratable_target_reports_no_generator:
    hypothesis draws a zoneinfo key and win32's CPython has no bundled
    tzdata (ModuleNotFoundError: No module named 'tzdata') -- an
    environment/dependency gap, not a code defect.
  - tests/unit/test_check_native_cargo_runners.py::test_finds_test_executable,
    tests/unit/fleet/test_manifest.py::test_load_manifest_ok: hardcoded
    /tmp/... and /abs/b POSIX absolute-path literals.
  - tests/unit/deploy/test_deploy_runner.py::test_generate_writes_files:
    asserts st_mode & 0o777 == 0o755, meaningless on win32 (no POSIX
    permission bits).
  - tests/unit/rapid_sweep_suite/test_filing.py::test_absolute_outside_root_is_kept_and_logged:
    Path("/definitely/not/under/tmp_path/x.py").is_absolute() is FALSE
    on win32 (no drive letter), so the function's own early return is
    correct and the test's premise is POSIX-only.
  - tests/system/test_cli_ticket.py::test_attach_without_path_fails_fast_off_tty,
    tests/test_tickets_evidence_cli.py::test_shell_metacharacters_do_not_reach_a_shell,
    tests/unit/test_skills_sync.py::test_run_defaults_to_home_claude_when_no_override_given,
    tests/unit/test_sync_claude_config_stale_guard_t3408.py::test_stale_file_skipped_forward_file_synced,
    tests/ticket_land_suite/test_land_core.py::test_record_land_commit_never_absorbs_a_bystanders_dirty_file,
    tests/unit/test_process_lock.py::test_two_checkouts_with_divergent_views_never_collide
    (git add -A returncode=130): message-wording / fixture-path-shape /
    environment assumptions, lower confidence, need a per-test read
    before a skip or fix lands.

(b) REAL PRODUCT DEFECTS -- roughly 20 of 49, NOT to be fixed under this
    ticket (each needs its own scoped leaf), including:
  - src/frob/app/ticket_runner/_new.py's scope-overlap warning builds
    str(p.relative_to(root)) instead of .as_posix() -- same
    already-fixed-elsewhere class as T-3662/T-3664 but a NEW call site
    (drives tests/unit/test_new_ticket_scope_overlap_warning.py's 2
    failures). Trivial, well-precedented one-line fix.
  - tests/ticket_land_suite/test_land_lock.py (2): PermissionError
    reading a lock file another handle holds open, and an
    orphan-reclaim log line that never fires -- Windows file-lock
    semantics (exclusive by default) differ from POSIX advisory locks;
    a correctness-relevant PLATFORM001-class gap in the land-lock
    primitive itself, not a test artifact.
  - tests/unit/test_graph_build_lock.py::test_two_processes_never_commit_to_the_same_cache_concurrently:
    same cross-process-lock-semantics family as above.
  - tests/unit/test_cycle_waiver.py (3): frob-cycle reports zero
    diagnostics for a planted, unwaived cycle on win32 -- looks like a
    silent-zero measurement gap in the cycle detector, not a message
    formatting issue; needs its own investigation before trusting
    CYCLE001 on win32 at all.
  - tests/test_ticket_land_lint_diff_attribution.py::test_pre_existing_violation_that_merely_shifted_lines_does_not_refuse:
    the pre-land lint-diff shifted-lines detector wrongly refuses on
    win32 -- plausibly CRLF-driven (every line reads as "shifted"),
    which would falsely block every Windows land if this path is ever
    exercised for real.
  - tests/unit/gates/test_profile_boundary.py (2), tests/unit/test_dup.py (1),
    tests/unit/arch_suite/test_misc.py::test_symref_matches_dsl_waiver_binding_exactly (1):
    further native-separator leaks in gate-internal path handling
    (same class as T-3662/T-3664, different call sites).
  - tests/test_tickets_mutation_evidence.py (2), tests/ticket_land_suite/test_wip.py (1),
    tests/unit/test_land_release_out_of_tree.py (1): git-diff-shaped
    behavioral divergences, plausibly CRLF/autocrlf-driven; unconfirmed.
  - tests/unit/test_process_lock.py::test_real_pool_worker_under_parent_shared_holder_completes
    (BrokenProcessPool) and ...test_counter_file_lives_under_git_common_dir
    (git.exe access violation, returncode 3221225786 = 0xC0000005):
    plausibly CI infra flake or a regression from T-3651's
    CREATE_NO_WINDOW change; unconfirmed, needs a second data point.
  - tests/unit/test_lang_primitives.py::test_symbol_tree_covers_span,
    tests/unit/strata/test_strata_core_gil.py::test_timeout_fires_during_worst_age:
    unconfirmed, need windows-side instrumentation.

(c) STRUCTURALLY IMPOSSIBLE (T-2963 territory): none identified in this
    49 -- the five T-3505 primitives (fcntl/sysconf/AF_UNIX/fork/charmap)
    are already closed; nothing here traces back to them.

ACCEPTANCE
- Fix bucket (a): correct the test-harness POSIX assumptions above --
  either a corrected cross-platform assertion/fixture, or an explicit
  pytest.mark.skipif(sys.platform == "win32", reason=...) naming the
  POSIX primitive, never a bare/unlabeled skip.
- Do NOT fix bucket (b) here -- file one leaf ticket per root-cause
  cluster under T-3505 (mirroring T-3661/T-3662/T-3664's pattern), each
  with its own scope.
- Re-measure after bucket (a) lands and update T-3505's body with the
  new stable count.
- This ticket does not touch the ci.yml windows-latest advisory flag --
  that is T-3512, owner's call, blocked on the real count this ticket
  produces.
