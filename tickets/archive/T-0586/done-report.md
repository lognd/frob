## Done report

## Done report

Changed:
src/frob/app/check_runner.py::_run_stamp_coverage

Evidence:
tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_passes_loaded_snapshot
tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns
tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1

Filed: none

Gates: frob check --ticket T-0586 --only lint clean; --only static clean (pre-existing
frob-exports WARNs only, unrelated); --only gates-native clean (pre-existing ARCH/PERF
waived warnings only); --only gates-security clean (pre-existing DEAD/PII/SEC waived
warnings only); --only gates-fast clean after re-running `frob ticket sweep T-0586`
(the two real blocking findings were PRE001 -- stale sweep after a mid-ticket
scope-add, fixed by the sweep re-run -- and SCOPE001 on uv.lock, which is a
pre-existing version-line flap artifact from the shared cargo/uv environment,
not a real change; `git checkout -- uv.lock` before every check run discarded it,
consistent with section 4b's land-owned-file rule). The two remaining gate:TEST
TEST010 findings (tests/test_perf_loop_invariant_effect_lock.py,
tests/system/test_spawn_budget.py) are pre-existing on main (verified via
`git show main:tests/test_perf_loop_invariant_effect_lock.py`), unrelated to this
ticket's scope, and not touched by this change.

`frob test --base main` surfaced ~20 failing tests across strata/doctor/perf/cli_check
modules unrelated to check_runner.py's stamp-coverage path or my test file -- none
reference `_run_stamp_coverage`/`stamp_coverage`/`test_stamp_coverage_*`; this looks
like shared-worktree-environment noise (concurrent sibling agents on the same host)
per the "Worktree natives artifact" memory precedent, not a regression from this
change. Targeted verification instead: `uv run pytest
tests/unit/test_app_runners_batch6.py -q` (55 passed) and
`uv run pytest tests/system/test_cli_check.py -k stamp_coverage -q` (1 passed).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_passes_loaded_snapshot` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_mode_calls_stamp_and_returns` (pytest node id, verified passing when recorded)
- `tests/unit/test_app_runners_batch6.py::TestCheckRunner::test_stamp_coverage_failure_exits_1` (pytest node id, verified passing when recorded)
