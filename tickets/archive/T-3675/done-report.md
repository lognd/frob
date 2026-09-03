## Done report

Evidence: 24 node ids recorded via `frob ticket evidence T-3675` --
tests/test_ci_workflow_matrix.py's TestWindowsStopBeforeDiagVariants
plus the Test-step env assertion, tests/unit/test_check_stop_before.py
(gating logic + an end-to-end run_check() integration check for two of
the four stop points), and tests/unit/test_conftest_hard_exit_guard.py
(gating, inventory-line formatting, and os._exit-argument capture via a
monkeypatched os._exit -- never a real hard exit inside the test
runner). All added in this worktree. `--check-repro --base-ref
7eea5bf75` (the test-only commit, committed before the ci.yml/
conftest.py/check/__init__.py fix landed on top of it) confirmed a
genuine FAILED_AT_PARENT repro.

Filed: none -- both parts fit within T-3675's declared scope. Also
folded in T-3666 (win32: conftest _write fixture converts LF to CRLF)
at the coordinator's request, since it is a tests/conftest.py-only fix
and this worktree already held that lease -- `_write` now passes
`newline=""` to `path.write_text`, a no-op on POSIX, verified against
tests/test_arch_gate.py (a non-gates_suite consumer of `_write`) since
tests/gates_suite/** is out of my declared scope to touch/run-as-a-
verification-target directly; the two originally-affected gates_suite
tests were not re-run here (win32-only failure, no local win32 repro
available), consistent with T-3666's own ticket body.

Gates: `uv run ruff check src tests` clean. `uv run ty check
src/frob/check/__init__.py tests/conftest.py
tests/unit/test_check_stop_before.py
tests/unit/test_conftest_hard_exit_guard.py` clean. Full pytest run of
tests/test_ci_workflow_matrix.py + tests/unit/test_check_stop_before.py
+ tests/unit/test_conftest_hard_exit_guard.py +
tests/unit/test_conftest_console_ctrl_guard.py + tests/unit/test_check.py
+ tests/test_arch_gate.py: 238 passed, 0 failed.

Grep of the pre-thread-start pipeline for win32-signal-adjacent code
(Part 2's observational request): no faulthandler timer or
signal.set_wakeup_fd call exists anywhere in src/frob outside the diag
scripts' own preambles. Two candidates found in the bracketed region,
noted in docs/modules/process.md's "Round 18" paragraph and neither
itself fixed here: (1) src/frob/lang/__init__.py::_run_parse_with_timeout
builds a fresh ThreadPoolExecutor(max_workers=1) + future.result(timeout=)
for every tree-sitter/strata-core parse the detect/tasks stages can
trigger -- the same executor.submit -> t.start() shape round 16's diag
stack trace named, just a different executor than
_run_tasks_concurrently's; (2) src/frob/process/_derived_lock.py's win32
backend uses msvcrt.locking for derived_state_lock (acquired at/before
the "lock" stop point) -- the only win32-specific blocking syscall
active that early. Windows CI itself is the actual verifier for the
win32-only diag/hard-exit behavior; that is the next run's job.

### Changed
```
 .github/workflows/ci.yml                    | 220 ++++++++++++++++++++++++++++
 docs/modules/process.md                     |  84 +++++++++++
 src/frob/check/__init__.py                  |  91 +++++++++++-
 tests/conftest.py                           |  97 +++++++++++-
 tests/test_ci_workflow_matrix.py            |  63 +++++++-
 tests/unit/test_check_stop_before.py        | 119 +++++++++++++++
 tests/unit/test_conftest_hard_exit_guard.py | 157 ++++++++++++++++++++
 tickets/T-3675/ticket.md                    |  42 +++++-
 8 files changed, 869 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants::test_all_four_points_have_their_own_step` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants::test_all_four_have_a_bounded_timeout` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants::test_each_step_sets_its_own_matching_point` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants::test_each_step_reuses_variant_a_script_and_fixture` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_sets_frob_test_hard_exit` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_false_when_env_unset` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_true_only_for_the_matching_point` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_unrecognized_value_matches_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_all_four_points_are_distinct_and_ordered` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_rejects_an_unknown_point_argument` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore::test_lock_point_returns_empty_result_before_any_stage` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore::test_tasks_point_returns_empty_result_before_submit` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore::test_no_stop_requested_runs_normally` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestHardExitRequested::test_false_when_env_unset` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestHardExitRequested::test_false_on_falsy_value` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestHardExitRequested::test_true_on_truthy_value` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestHardExitRequested::test_no_platform_restriction` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestDescribeTeardownBlockers::test_line_has_the_expected_marker_and_sections` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestDescribeTeardownBlockers::test_includes_the_current_thread_with_its_daemon_flag` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestDescribeTeardownBlockers::test_lists_an_extra_non_daemon_thread_by_name` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestDescribeTeardownBlockers::test_empty_children_list_when_none_active` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestMaybeHardExitAfterSessionFinish::test_no_op_when_not_requested` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestMaybeHardExitAfterSessionFinish::test_hard_exits_with_the_sessions_real_exitstatus` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_hard_exit_guard.py::TestMaybeHardExitAfterSessionFinish::test_falls_back_to_the_hook_exitstatus_when_session_exitstatus_is_not_an_int` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 24 passed (from 24 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
