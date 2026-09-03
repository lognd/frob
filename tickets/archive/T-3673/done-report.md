## Done report

Evidence: 25 node ids recorded via `frob ticket evidence T-3673` (see
this ticket's own evidence list) -- tests/test_ci_workflow_matrix.py's
TestWindowsTrivialPythonDiagVariant/TestWindowsImportOnlyDiagVariant/
TestWindowsMitigationDiagVariant plus the Test-step env assertion, and
the new tests/unit/test_conftest_console_ctrl_guard.py file, all added
in this worktree. `--check-repro --base-ref c30778990` (the test-only
commit, committed before the ci.yml/tests/conftest.py fix landed on
top of it) confirmed a genuine FAILED_AT_PARENT repro for the trivial-
python-variant existence test.

Filed: none -- all planned work fit within T-3673's declared scope; no
out-of-scope discoveries surfaced.

Gates: `uv run ruff check src tests` clean. `uv run ty check
tests/unit/test_conftest_console_ctrl_guard.py` clean (fixed one
call-non-callable finding on the fake win32 handler's object-typed
holder via a `Callable` cast, discovered by the land's own pre-land
gate). Full pytest run of tests/test_ci_workflow_matrix.py +
tests/unit/test_conftest_console_ctrl_guard.py: 63 passed, 0 failed.
Windows CI itself -- the actual verifier for the win32-only variants
(e)/(f)/(a2) and the new suite guard -- has not run yet; that is the
next CI run's own job, by this ticket's own design (a control/
mitigation-validation round, not a local-repro-able fix).

### Changed
```
 .github/workflows/ci.yml                       | 257 +++++++++++++++++++++++++
 docs/modules/process.md                        |  61 ++++++
 tests/conftest.py                              |  94 +++++++++
 tests/test_ci_workflow_matrix.py               | 186 ++++++++++++++++++
 tests/unit/test_conftest_console_ctrl_guard.py | 197 +++++++++++++++++++
 tickets/T-3673/ticket.md                       |  35 +++-
 6 files changed, 829 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsTrivialPythonDiagVariant::test_trivialpython_diag_step_exists_and_runs_on_windows` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTrivialPythonDiagVariant::test_trivialpython_diag_step_has_a_bounded_timeout` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTrivialPythonDiagVariant::test_trivialpython_diag_step_never_imports_frob` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTrivialPythonDiagVariant::test_trivialpython_diag_step_installs_the_signal_logger` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTrivialPythonDiagVariant::test_trivialpython_diag_step_just_sleeps` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTrivialPythonDiagVariant::test_trivialpython_diag_step_keeps_uv_ancestry` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsImportOnlyDiagVariant::test_importonly_diag_step_exists_and_runs_on_windows` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsImportOnlyDiagVariant::test_importonly_diag_step_has_a_bounded_timeout` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsImportOnlyDiagVariant::test_importonly_diag_step_imports_frob_and_nothing_else` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsImportOnlyDiagVariant::test_importonly_diag_step_imports_before_sleeping` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsMitigationDiagVariant::test_mitigation_diag_step_exists_and_runs_on_windows` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsMitigationDiagVariant::test_mitigation_diag_step_has_a_bounded_timeout` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsMitigationDiagVariant::test_mitigation_diag_step_sets_the_env_var` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsMitigationDiagVariant::test_mitigation_diag_step_reuses_variant_a_script_and_fixture` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsMitigationDiagVariant::test_mitigation_diag_step_fails_the_step_on_exit_130` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_sets_frob_test_ignore_console_ctrl` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_console_ctrl_guard.py::TestTestConsoleCtrlIgnoreRequested::test_false_on_non_win32_even_when_env_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_console_ctrl_guard.py::TestTestConsoleCtrlIgnoreRequested::test_false_on_win32_when_env_unset` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_console_ctrl_guard.py::TestTestConsoleCtrlIgnoreRequested::test_false_on_falsy_value` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_console_ctrl_guard.py::TestTestConsoleCtrlIgnoreRequested::test_true_on_win32_when_truthy` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_console_ctrl_guard.py::TestInstallAndUninstallTestConsoleCtrlIgnoreGuard::test_no_op_when_not_requested` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_console_ctrl_guard.py::TestInstallAndUninstallTestConsoleCtrlIgnoreGuard::test_installs_and_removes_exactly_one_handler` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_console_ctrl_guard.py::TestInstallAndUninstallTestConsoleCtrlIgnoreGuard::test_handler_swallows_ctrl_c_and_ctrl_break_only` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_console_ctrl_guard.py::TestInstallAndUninstallTestConsoleCtrlIgnoreGuard::test_uninstall_without_install_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_console_ctrl_guard.py::TestRealPlatformNeverRequestsGuardByDefault::test_unset_in_this_repos_own_default_env` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 25 passed (from 25 evidence id(s))
- gates: 21 error(s), 4276 warning(s), 897 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3673/ticket.md, DOC007@tests/test_tickets_leases.py, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, DRIFT002@tests/test_tickets_leases.py, DUP001@tests/test_ci_workflow_matrix.py, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, PERF003@src/frob/refactor/_scan.py, PRE001@tickets/T-3673, REF002@src/frob/process/_lock_msvcrt.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json, WIRE001@tests/conftest.py
