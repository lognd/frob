## Done report

Re-added the subprocess/pool-worker coverage measurement T-2240's Makefile
retirement dropped without porting: native_coverage_refresh had no
COVERAGE_PROCESS_START mechanism at all, so any subprocess (a CLI test
running frob in a tmp fixture repo, a ProcessPoolExecutor gate worker)
spawned during a pytest pass measured nothing -- T-1235's original "Loss A"
bug, reintroduced through the new code path.

MEASURED THE GAP FIRST, before writing the fix: a single real subprocess
test (tests/system/test_cli_doctor.py::TestDoctorCli::
test_doctor_reports_healthy_when_natives_present, which spawns `python -m
frob doctor` in a tmp cwd with no env override) run under `pytest --cov`
with COVERAGE_PROCESS_START unset (the current native-path behavior)
showed src/frob/doctor.py at 0% covered -- 0 of 292 statements, despite
the subprocess genuinely executing hundreds of lines before erroring.
Same test, same subprocess call, COVERAGE_PROCESS_START pointed at a
freshly generated absolute-path rc: 57% covered, 185 of 292 statements
newly registered. The remaining 107 lines this one test does not reach
still correctly reported uncovered both times -- the fix measures real
execution, it does not inflate the numbers. Re-ran the same measurement
against the real _pytest_subprocess_env() function (not a fake) after
writing the fix, with an identical result, confirming the wiring is real
end to end, not just correct in isolation.

Read T-1235's actual historical implementation (git log --grep T-1235 --
Makefile, commits 07995d6fa and e020c7887) before designing anything: its
mechanism (a dedicated rc with absolute source/data_file, [paths] remap
back to the relative key, concurrency=multiprocessing+thread + sigterm=
true) is still the right fix -- only the GENERATION SITE needs to move
from a Makefile recipe to Python. Confirmed pyproject.toml's own
[tool.coverage.run] concurrency/sigterm settings (T-1235's "Loss B" fix)
were never lost -- only Loss A's rc-generation was, so this ticket ports
Loss A only, unchanged from the original mechanism.

Implementation: _write_coverage_subprocess_rc(root, cov_target) generates
.frob/coverage-subprocess.rc with absolute paths (same content shape as
the retired Makefile recipe); _pytest_subprocess_env(root, cov_target)
wraps it into an env dict with COVERAGE_PROCESS_START set. Threaded an
env: dict[str, str] | None = None parameter through every subprocess seam
a pytest pass goes through (_spawn, _spawn_with_watchdog,
_start_watchdog_process's two Popen calls, _pytest_outcome,
_retry_after_worker_crash) -- defaults to None (inherit os.environ
unchanged, the pre-fix behavior) everywhere except _run_full_suite and
_run_incremental_or_restamp, which now build the env once per pass and
pass it through. coverage xml/combine calls (_run) are untouched --
they never needed COVERAGE_PROCESS_START.

New tests (tests/test_coverage.py::TestSubprocessCoverageRc, 5 tests)
carry the exact same claims the deleted tests/unit/test_makefile_
coverage.py::TestSubprocessRcIsAbsoluteAndConcurrencyAware class made
(absolute source/data_file, concurrency+sigterm declared, [paths] remap),
plus a native_coverage_refresh-level wiring test proving the real entry
point actually passes the env through, not just that the two leaf
helpers work in isolation. Updated 12 existing _fake_spawn monkeypatches
in tests/test_coverage.py to accept the new env kwarg (**_kw) so the
signature change didn't silently break already-passing tests. Full
tests/test_coverage.py: 56 passed.

Deliberately did NOT touch T-1205/T-1235/T-1397/T-1526's own evidence
bindings or T-2366's block -- that repointing decision belongs to T-2366,
now unblocked, and needs its own honest judgment call (new tests exist
now, but they are NOT the same test identities the archived tickets'
acceptance criteria named).

### Changed
```
 src/frob/testing/_coverage_refresh.py | 125 +++++++++++++++++++++++++++---
 tests/test_coverage.py                | 141 ++++++++++++++++++++++++++++++----
 tickets/T-2527/ticket.md              |   9 ++-
 3 files changed, 248 insertions(+), 27 deletions(-)
```

### Evidence
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_rc_uses_absolute_source_and_data_file` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_rc_declares_multiprocessing_and_sigterm` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_rc_remaps_paths_back_to_source` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_env_carries_coverage_process_start_pointed_at_the_rc` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestSubprocessCoverageRc::test_full_run_passes_coverage_process_start_env_to_spawn` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_full_run_when_no_stamp_exists` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/testing/_coverage_refresh.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV005@src/frob/testing/_coverage_refresh.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@src/frob/testing/_coverage_refresh.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT002@src/frob/testing/_coverage_refresh.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2527/src/frob/app/ticket_runner/_verify.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
