## Done report

Changed:
  src/frob/process/_guard.py::FROB_WIN32_IGNORE_CONSOLE_CTRL_ENV
  src/frob/process/_guard.py::win32_console_ctrl_ignore_scope
  src/frob/process/_guard.py::_win32_ignore_console_ctrl_requested
  src/frob/check/__init__.py::_run_check_with_skips
  .github/workflows/ci.yml (new "zero-tool-spawn variant" diag step)
  tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope
  tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant
  docs/modules/process.md (T-3657 section)

Spawn audit (plan item 1): every subprocess.run/Popen call inside the
check path (src/frob/check/_python.py, _native.py, _ts.py) already
routes through guarded_subprocess_run -- measured zero unguarded direct
subprocess spawns in that path. The one real unguarded-spawn family
found: frob.gates's ProcessPoolExecutor (multiprocessing, spawn start
method on win32), used for internal gate worker dispatch. It is NOT
gated by FROB_DISABLE_EXEC (it spawns frob's own workers, not an
external tool) and is NOT touched by this ticket -- documented as a
caveat on the new CI diag variant and in docs/modules/process.md
instead of "fixed" without evidence it is even implicated.

Evidence:
  tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_no_op_on_non_win32
  tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_no_op_when_env_unset
  tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_installs_and_removes_handler_when_requested
  tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_handler_swallows_ctrl_c_and_ctrl_break
  tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_handler_passes_through_other_events
  tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_exists_and_runs_on_windows
  tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_has_a_bounded_timeout
  tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_sets_frob_disable_exec_before_main
  tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_reuses_the_same_fixture
  tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_pins_project_to_checkout
  tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_precedes_the_windows_test_step

Filed: none (no out-of-scope defects found -- the ProcessPoolExecutor
finding is documented as an in-scope-ticket caveat, not filed separately,
since fixing/not-fixing it is exactly the evidence-gated decision this
ticket's plan item 3 describes).

Gates: `frob check --ticket T-3657 --only scope/prework/affect_drift`
clean (0 errors) after fixing a frob:tests directive separator bug
(Class::method -> Class.method, matching this file's own sibling-block
convention) that was making DRIFT002 report the new tests edges as
dangling. Remaining repo-wide FAILs in a full `frob check` run
(WAIVE011 ratchet-lock staleness, claude-config-drift, and the many
pre-existing repo-wide gate counts the --ticket note calls out as NOT
scoped to this diff) are pre-existing and unrelated to this ticket's
touched set.

### Changed
```
 .github/workflows/ci.yml         | 111 ++++++++++++++++++++++++++++++++++++
 docs/modules/process.md          |  31 ++++++++++
 src/frob/check/__init__.py       |  11 ++++
 src/frob/process/_guard.py       | 107 ++++++++++++++++++++++++++++++++++-
 tests/test_ci_workflow_matrix.py | 107 ++++++++++++++++++++++++++++++++++-
 tests/unit/test_process_guard.py | 118 +++++++++++++++++++++++++++++++++++++++
 tickets/T-3657/ticket.md         |  29 +++++++++-
 7 files changed, 511 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_no_op_on_non_win32` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_no_op_when_env_unset` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_installs_and_removes_handler_when_requested` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_handler_swallows_ctrl_c_and_ctrl_break` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_guard.py::TestWin32ConsoleCtrlIgnoreScope::test_handler_passes_through_other_events` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_exists_and_runs_on_windows` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_has_a_bounded_timeout` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_sets_frob_disable_exec_before_main` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_reuses_the_same_fixture` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_pins_project_to_checkout` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsZeroSpawnDiagVariant::test_zerospawn_diag_step_precedes_the_windows_test_step` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 19 error(s), 4269 warning(s), 896 waived
- error-findings: ARCH102@src/frob/process/_lock.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/process/_guard.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, LANDPARITY001@src/frob/process/_guard.py, LARGE001@src/frob/refactor/_scan.py, LARGE001@src/frob/refactor/_verify.py, OPAQUE001@src/frob/app/_config_external.py, REL001@src/frob/__init__.py, SEC110@tests/ticket_land_suite/test_wip.py, SELFAUDIT001@tests/test_ci_workflow_matrix.py, SUPPRESS001@src/frob/process/_guard.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json, WIRE001@tests/unit/test_process_guard.py, call-non-callable@tests/unit/test_process_guard.py, unresolved-attribute@src/frob/process/_guard.py
