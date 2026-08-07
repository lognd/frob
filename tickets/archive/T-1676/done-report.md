## Done report

Removed the all-passing-tests requirement from the coverage artifact path.

WHAT CHANGED

`_spawn` is now the single subprocess seam in the module, returning the
CompletedProcess whenever the process actually ran. Two readings sit on
top of it: `_run` (non-zero means no usable output -- still correct for
`coverage xml`) and `_pytest_outcome` (non-zero means a red suite, whose
coverage data is still exactly what the caller asked for). The pytest
passes now use the latter, and every branch returns a `_PytestPass`
carrying `ran` / `degraded` / `exit_code` instead of a bare bool.

`CoverageRefreshError.PytestFailed` is gone, replaced by `PytestRefused`.
That rename is the whole point: the ONLY remaining abort is a spawn that
never happened (`FROB_DISABLE_EXEC=1`), because that is the only case
with genuinely no measurement to keep.

`_write_run_provenance` records `.frob/coverage-run.json` on every run --
degraded or not, deliberately, so a previous run's degraded note can
never be misread as a property of the current artifact. It is
side-effect-only and best-effort: the coverage data is already stamped by
the time it runs, and losing the note must not turn a good refresh into a
failure.

WHY IT IS SAFE TO STAMP A DEGRADED ARTIFACT

Two independent guards already hold and were verified, not assumed:
`stamp_coverage`'s `module_join_fraction` deflation floor refuses a
coverage.xml that was genuinely truncated, and `write_coverage_lock`'s
ratchet refuses to lower a committed floor unless `allow_decrease=True`
is passed deliberately. So a degraded run can raise a floor or clear a
violation; it cannot quietly lower the bar. A NEW low-coverage finding
sourced from a degraded run is still suspect -- documented, not silently
tolerated.

EVIDENCE

`test_red_suite_keeps_coverage_data` is the inverted form of the deleted
`test_pytest_failure_is_err`, which asserted precisely the behavior this
ticket removes. It is bound FIRST so BUG002 designates it, and it fails
at the parent commit. `test_refused_spawn_is_err` locks the one remaining
abort; `test_green_suite_records_not_degraded` locks the stale-note case.

The three existing tests that patched `_run` to intercept pytest were
repointed at `_spawn`. Left alone they would have silently stopped
observing the pytest argv and spawned real pytest runs inside the unit
suite.

COLLATERAL, DISCLOSED

T-1205 and T-1516 both bound the deleted test as evidence; both were
rebound to `test_refused_spawn_is_err` via `frob ticket evidence
--replace --archived`, which is why `tickets-archive.md` is in scope.
`design/frob.strata` gained two capability declarations the new file
write and its test reads genuinely require (core `fs.write`, testsuite
`fs.read`).

NOT DONE HERE

The run that motivated this ticket did not merely fail -- it HUNG for
five hours with no deadline and no watchdog. That is T-1677, filed
separately and rated critical; this ticket makes a failed run survivable
but does nothing about a run that never ends. T-1672 covers retrying the
unfinished work units after a worker dies.

### Changed
(no changed files detected)

### Evidence
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_red_suite_keeps_coverage_data` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_refused_spawn_is_err` (pytest node id, verified passing when recorded)
- `tests/test_coverage.py::TestNativeCoverageRefresh::test_green_suite_records_not_degraded` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 707 warning(s), 713 waived
- error-findings: none (measured, zero errors)
