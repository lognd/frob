## Done report

Evidence: 27 node ids recorded via `frob ticket evidence T-3683` (see
this ticket's own evidence list) -- tests/test_ci_workflow_matrix.py's
TestWindowsStopBeforeDiagVariants (extended to 7 points) plus the new
Test-step FROB_TEST_MIDRUN_WATCHDOG_SECONDS assertion,
tests/unit/test_check_stop_before.py (extended with entry/console-
scope/admission gating + end-to-end run_check() coverage), and the new
tests/unit/test_conftest_midrun_watchdog.py (threshold parsing, the
pure stall predicate, the watchdog thread body, and the hard-exit
announce path -- os._exit monkeypatched throughout, never a real hard
exit inside the test runner). All added in this worktree.
`--check-repro --base-ref 7bad27a95` (the test-only commit, committed
before the check/__init__.py + conftest.py + ci.yml fix landed on top
of it) confirmed a genuine FAILED_AT_PARENT repro.

Part A (src/frob/check/__init__.py): restructured the console-ctrl-
scope/admission-budget/derived-state-lock entry from one `with (...)`
tuple into a `contextlib.ExitStack` sequential entry (identical end
state/lock order for a normal run), landing 3 new
FROB_CHECK_STOP_BEFORE points -- "entry" (before ANY context manager),
"console-scope" (after console-ctrl scope, before admission budget),
"admission" (after admission budget, before derived-state lock) --
ahead of round 18's original "lock"/"detect"/"tasks"/"submit". 3
matching CI diag sub-variant steps added to .github/workflows/ci.yml.
Deliberately did NOT touch src/frob/process/_derived_lock.py: T-3681
held a live in-progress lease on that file for the whole duration of
this ticket (scope-collision refused at `frob ticket start` on first
attempt; narrowed T-3683's own scope to drop it and docs/modules/
process.md rather than wait on or coordinate a shared edit). This
round's own CI run is therefore the thing that will actually confirm
or clear the msvcrt.locking suspicion the coordinator named -- if
"admission" comes back clean and "lock" dirty in that run, the
follow-up ticket (filed then, once T-3681 has landed and the file's
lease is free) targets exactly that file with the CI evidence already
in hand from this round.

Part B (tests/conftest.py): added an independent mid-run watchdog
(FROB_TEST_MIDRUN_WATCHDOG_SECONDS, unit-tested gating/predicate/
thread-body/announce path), armed at 300s in the windows Test step's
own env: block. Diagnostic-first per the coordinator's own framing --
the real fix is Part A (or its in-scope follow-up); this only ensures
a future mid-run wedge is never silent again.

docs/modules/process.md was left untouched this round for the same
scope-collision reason (T-3681 held a live lease on it too) -- the
Round 19 documentation paragraph is queued as the very next small
follow-up once T-3681's land frees that file, so the doc-drift never
compounds across rounds.

Gates: `uv run ruff check src tests` clean. `uv run ty check
src/frob/check/__init__.py tests/conftest.py
tests/unit/test_check_stop_before.py
tests/unit/test_conftest_midrun_watchdog.py
tests/test_ci_workflow_matrix.py` clean. Full pytest run of
tests/test_ci_workflow_matrix.py + tests/unit/test_check_stop_before.py
+ tests/unit/test_check.py + tests/unit/test_conftest_midrun_watchdog.py
+ tests/unit/test_conftest_hard_exit_guard.py +
tests/unit/test_conftest_console_ctrl_guard.py +
tests/unit/test_conftest_stackdump.py: 267 passed, 0 failed. Windows CI
itself is the actual verifier for the win32-only stop-point/watchdog
behavior; that is the next run's job, per this round's own design.

### Changed
```
 .github/workflows/ci.yml                    | 171 ++++++++++++++++++++++++++++
 src/frob/check/__init__.py                  |  71 +++++++++---
 tests/conftest.py                           | 161 ++++++++++++++++++++++++++
 tests/test_ci_workflow_matrix.py            |  56 ++++++---
 tests/unit/test_check_stop_before.py        |  87 +++++++++++---
 tests/unit/test_conftest_midrun_watchdog.py | 160 ++++++++++++++++++++++++++
 tickets/T-3683/ticket.md                    |  36 ++++++
 7 files changed, 699 insertions(+), 43 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants::test_all_seven_points_have_their_own_step` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants::test_all_seven_have_a_bounded_timeout` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants::test_each_step_sets_its_own_matching_point` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants::test_each_step_reuses_variant_a_script_and_fixture` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_sets_frob_test_midrun_watchdog_seconds` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_false_when_env_unset` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_true_only_for_the_matching_point` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_unrecognized_value_matches_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_all_seven_points_are_distinct_and_ordered` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestCheckStopBefore::test_rejects_an_unknown_point_argument` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore::test_entry_point_returns_empty_result_before_any_context_manager` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore::test_console_scope_point_returns_empty_result_before_admission_budget` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore::test_admission_point_returns_empty_result_before_derived_state_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore::test_lock_point_returns_empty_result_before_any_stage` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore::test_tasks_point_returns_empty_result_before_submit` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_stop_before.py::TestRunCheckHonorsStopBefore::test_no_stop_requested_runs_normally` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestMidrunWatchdogThresholdS::test_none_when_unset` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestMidrunWatchdogThresholdS::test_none_when_zero` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestMidrunWatchdogThresholdS::test_none_when_negative` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestMidrunWatchdogThresholdS::test_none_when_not_numeric` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestMidrunWatchdogThresholdS::test_parses_a_positive_value` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestMidrunStallDetected::test_false_before_threshold_elapsed` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestMidrunStallDetected::test_true_at_exactly_the_threshold` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestMidrunStallDetected::test_true_well_past_the_threshold` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestRunMidrunWatchdog::test_fires_hard_exit_when_no_progress_and_never_stopped` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestRunMidrunWatchdog::test_never_fires_once_stop_event_is_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_conftest_midrun_watchdog.py::TestAnnounceMidrunStallAndHardExit::test_hard_exits_with_status_1_and_prints_the_inventory_line` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 27 passed (from 27 evidence id(s))
- gates: 14 error(s), 4308 warning(s), 912 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/check/__init__.py, COV003@tests/test_ci_workflow_matrix.py, COV003@tests/unit/test_check_stop_before.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, DUP001@tests/test_ci_workflow_matrix.py, DUP001@tests/unit/test_check_stop_before.py, PERF003@src/frob/refactor/_scan.py, PERF004@src/frob/refactor/_scan_carry.py, REL001@src/frob/__init__.py, WAIVE011@frob-ratchet.lock.json, WIRE001@tests/conftest.py
