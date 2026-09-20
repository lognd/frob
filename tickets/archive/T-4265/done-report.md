## Done report

Changed:
- .github/workflows/ci.yml -- deleted the contiguous block of 14 windows-only
  "Diagnose frob check hang on windows..." diagnostic step blocks (T-3589's
  variant (a), T-3657's zero-tool-spawn variant, T-3670's direct-python and
  pool-preload-disabled variants, T-3673's trivial-python/import-only/
  mitigation-enabled variants, T-3683's stop-before entry/console-scope/
  admission variants, T-3675's stop-before lock/detect/tasks/submit variants)
  and the historical comment paragraph introducing them -- 1,108 lines
  removed, nothing added. Left untouched: the real
  `Test (windows, timed with hang guard)` step, every comment explaining its
  own permanent mitigations (FROB_TEST_IGNORE_CONSOLE_CTRL, FROB_TEST_HARD_EXIT,
  FROB_TEST_MIDRUN_WATCHDOG_SECONDS), and the job-level `continue-on-error`
  advisory flag (T-4236, explicitly out of scope here).
- tests/test_ci_workflow_matrix.py -- removed the eight test classes and
  eight helper functions that existed only to pin the shape of the deleted
  diagnostic steps (TestWindowsDiagStepResolvesFrobCheckoutEnv,
  TestWindowsZeroSpawnDiagVariant, TestWindowsDirectPythonDiagVariant,
  TestWindowsNoPoolPreloadDiagVariant, TestWindowsTrivialPythonDiagVariant,
  TestWindowsImportOnlyDiagVariant, TestWindowsMitigationDiagVariant,
  TestWindowsStopBeforeDiagVariants, TestWindowsDiagStepFixtureIsAClassifiableProject,
  TestCodeLinesArrayLiteralIsSyntacticallyBalanced, and the diag-only methods
  of TestWindowsDiagStepDoesNotGateTheJob/TestWindowsDiagStepRunsUnbudgeted) --
  865 lines removed. The handful of methods that asserted properties of the
  REAL Test (windows...) step (env vars, --timeout=600, -rA/--tb=short,
  windows-only gating, no continue-on-error) were kept, not deleted -- moved
  into a new class, TestWindowsTestStepMitigationsStayPinned, since their old
  home's docstring/name was itself diagnostic-step-specific.
  `test_test_step_is_untouched_and_still_windows_only`'s docstring was
  reworded (it referenced the now-deleted diagnostic step by name) without
  touching its assertions.

Confirmed individually before deleting each block (`uv run frob ticket show`):
T-3589 done, T-3657 done, T-3670 done, T-3673 done, T-3675 done, T-3683 done.

Verified via `uv run pytest -q tests/test_ci_workflow_matrix.py`: 17 passed
(52 existed before; 35 were diagnostic-step-only and removed with their
target).

Windows leg wall-clock, acceptance [3]: NO MEASURABLE CHANGE, reported
plainly rather than as a speedup. This is a step-level decomposition of the
last completed windows leg prior to this change (not a before/after of this
branch's own CI run, which was not needed once the decomposition was
available): the fourteen diagnostic step blocks totalled ~174 seconds across
the whole ~64-minute (3,824s) job -- 124 of those seconds in the
zero-tool-spawn variant (T-3657) alone, the rest five to ten seconds each.
The other ~57 minutes (3,424s) is the real `Test (windows, timed with hang
guard)` step itself, which then fails and causes the gate step to be skipped
entirely. Removing the diagnostics therefore does not and was not expected
to measurably shorten the windows leg once decomposed this way; the filing
ticket's inference that this scaffolding was "a plausible large share" of
the gap is retracted, not repeated. The cleanup is justified purely on its
own terms -- 14 step blocks and ~1,100 lines characterising a fixed defect
whose 6 originating tickets are all closed -- not on a timing win.

Noted, not fixed here (explicitly out of scope for this ticket): the real
driver of the windows leg's length is the Test step's own ~57-minute run,
which then fails outright. The coordinator has this observation and will
file it separately if warranted.

Filed: none.

Gates: `frob check --ticket T-4265` clean on gate:SCOPE/gate:PREWORK (after
`frob ticket sweep T-4265`) and the ticket-scoped parts of gate:COV/gate:FMT/
gate:AFFECT. Remaining repo-wide FAILs (gate:ARCH 1 pre-existing error in
src/frob/app/ticket_runner/_land_cmd.py, gate:DRIFT 3 pre-existing errors in
src/frob/gates/invariants.py and src/frob/tickets/_evidence.py already
waived pending a blocked `frob ack`, gate:COV 84 errors) are explicitly
REPO-WIDE per `frob check`'s own --ticket scope-note and predate/are outside
this change, with one caveat: deleting the 35 diagnostic-only tests orphans
COV003 evidence citations on the already-closed/archived T-3589/T-3597/
T-3604/T-3609/T-3619/T-3624/T-3633/T-3637/T-3652/T-3657/T-3670/T-3673/
T-3675/T-3683 (their bound evidence node ids no longer resolve). This is the
direct, expected, ticket-sanctioned consequence of deleting tests those
closed tickets cited as evidence for already-shipped, already-verified
fixes, not a new defect in the current tree. Not fixed here (out of scope:
it means editing already-archived ticket ledger entries, not
`.github/workflows/ci.yml` or `tests/test_ci_workflow_matrix.py`).

`uv run frob test --base main`: 1 python test selected, PASS.

A PR (#11) was opened only to get an independent windows-leg timing sample;
it was closed without merging once the step-level decomposition above made
that unnecessary, and its remote branch was deleted. This repo lands
through `frob ticket land`, not PR merge.

### Changed
```
 .github/workflows/ci.yml         | 1108 --------------------------------------
 tests/test_ci_workflow_matrix.py |  877 +-----------------------------
 tickets/T-4265/ticket.md         |   70 ++-
 3 files changed, 79 insertions(+), 1976 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_includes_windows_and_macos` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_is_fail_fast_false` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_is_gated_to_ubuntu_only` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_does_not_shell_to_make` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_stamp_baseline_is_bare_not_chunked_by_only` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_calls_frob_coverage_full` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_suite_runs_under_coverage_once_not_twice` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_ignore_console_ctrl` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_hard_exit` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_sets_frob_test_midrun_watchdog_seconds` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_raises_per_test_timeout_to_600` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_surfaces_failure_tracebacks` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_test_step_is_untouched_and_still_windows_only` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_ubuntu_test_step_no_reruns_flakes` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_macos_test_step_no_reruns_flakes` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes::test_windows_test_step_no_reruns_flakes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 17 passed (from 17 evidence id(s))
- gates: 9 error(s), 4529 warning(s), 943 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV001@src/frob/vet/_bare_toolchain.py, COV003@tests/test_ci_workflow_matrix.py, COV003@tests/test_excludes.py, COV003@tests/test_tickets.py, COV003@tests/test_tickets_evidence_cli.py, DRIFT001@src/frob/gates/__init__.py, DRIFT001@src/frob/gates/_rule_id_scan.py, DRIFT002@src/frob/check/_python.py
