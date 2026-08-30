---
id: T-3488
title: 'macOS-only CI failures: characterize the 32-test set (GNU timeout, runner
  git identity, /proc live-process scans, citation scans returning 0, scope ; validation)
  and fix the mechanical buckets'
state: in-progress
kind: bug
origin: agent
created: '2026-08-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/system/test_ci_hang_guard_positive_control.py
- tests/test_ticket_leases.py
- tests/system/test_natives_build_integration.py
- docs/design/macos-portability.md
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
MEASURED on GitHub Actions run 33311990183 (macos-latest, HEAD 986f8671c,
2026-08-30): with the 40m budget (T-3482) macOS completes the suite in 26.5
min with 39 failures. Ubuntu on the same HEAD: 6 (all owned by T-3484 /
T-3324 / stage-groups / serial-pools tickets). Subtracting the shared set,
the macOS-ONLY set is ~32 tests and has been stable across the last 5
completed macOS runs (51 -> 38 -> 39 -> 39). This ticket owns
CHARACTERIZATION + the cheap fixes; file one follow-up per remaining
root-cause bucket, like T-3076 did for Windows.

BUCKETS (assertion text from the run):
 A. GNU coreutils absent (2): tests/system/test_ci_hang_guard_positive_control.py
    FileNotFoundError: 'timeout'. macOS has no GNU `timeout`; ci.yml already
    documents this (T-3250). Fix: the positive control must use the same
    bash `kill -ABRT` watcher shape ci.yml uses on macOS, or skip ONLY when
    `shutil.which("timeout")` is None with the PLATFORM001 boundary stated.
 B. Runner git identity preset (1): tests/test_ticket_leases.py::...::
    test_identity_less_environment_falls_back_to_throwaway_git_identity
    assert 'Anka <runner...92399F.local>' == 'frob-bot <...>'. The macOS
    runner image ships a global user.name/email; the test must scrub
    GIT_CONFIG_GLOBAL/HOME (set GIT_CONFIG_GLOBAL=/dev/null) to be hermetic.
 C. Live-process / cwd detection (7): tests/unit/test_land_finish_guard.py (4),
    tests/test_ticket_leases.py::TestRemoveWorktree::test_keeps_a_live_process_worktree
    ('removed' == 'kept:live'), tests/test_worktree_guard.py (1),
    tests/test_mutate_journal.py::test_recycled_pid_with_mismatched_starttime_is_treated_stale
    (0 == 1). The scanner reads /proc (Linux-only); macOS needs `lsof -p`/
    `ps -o lstart` equivalents or the PLATFORM001 declared boundary with the
    tests asserting the DECLARED direction (T-3076 pattern).
 D. Citation / text scans return 0 (13): tests/test_tickets_live_tracker.py (11,
    all `assert 0 == N`), tests/test_gates.py::TestWireGate (2, `assert not True`).
    Same shape: a scan that finds N on Linux finds 0 on macOS. Suspects:
    `git grep` flag differences, BSD `grep -P`, or path case-insensitivity
    (APFS) breaking a path-keyed match. Measure one of them on a macOS box
    or via the CI log with -vv; this bucket is one root cause.
 E. Scope ';' validation (3): tests/test_tickets.py::TestScopeGlobValidation
    (DID NOT RAISE / assert None == 'src/...;src/...'). A ';'-joined scope
    entry is accepted on macOS but refused on Linux -- likely a shlex/posix
    difference in how the CLI splits args, or a glob library difference.
 F. Subprocess/env (4): test_tickets_evidence_cli.py::test_shell_metacharacters_
    do_not_reach_a_shell (assert False), test_app_daemon_proxy.py::TestQuery::
    test_remote_error_falls_back (Unreachable is RemoteError -- AF_UNIX path
    length limit on macOS?), test_coverage.py::TestNativeCoverageRefresh::
    test_full_run_produces_coverage_xml_after_worker_crash_recovery (1 == 2),
    test_coverage_sigterm.py::test_repeated_sigterm_terminates_in_bounded_time
    (PermissionError: Operation not permitted -- killpg on a group the
    runner's sandbox owns; use the child's own pgid).
 G. Toolchain (1): test_natives_build_integration.py::test_build_natives_compiles_
    and_imports_real_crate -- asserts on cargo's colored "Updating crates.io
    index" stderr; strip ANSI / set CARGO_TERM_COLOR=never in the test.
 H. test_ticket_land_lint_diff_attribution.py::...::test_pre_existing_violation_
    that_merely_shifted_lines_does_not_refuse (SystemExit: 1) -- unknown, measure.

ACCEPTANCE: buckets A, B, G fixed here (hermetic, no skips except A's
declared boundary); one follow-up ticket filed per remaining bucket (C, D,
E, F, H) with the measured root cause; docs/design/macos-portability.md
created mirroring docs/design/windows-portability.md. The macOS leg stays
REQUIRED (not advisory): unlike Windows its set is small and mechanical.
