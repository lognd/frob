## Done report

CI ran the full 13k-test suite TWICE per push: once for pass/fail (pytest in the Test step) and once under coverage (frob coverage --full in the T-1366 stamp step). The second run is the ubuntu leg's long pole and, memory-capped to -n 2 to avoid an OOM worker-kill, blew its 3600s wall-clock deadline.

This adds `frob coverage --full --fail-on-degraded`: coverage_runner reads the run provenance (.frob/coverage-run.json) that native_coverage_refresh already writes and exits non-zero when the suite ran RED -- a pytest exit != 0 that is NOT an xdist worker-crash (a worker-crash is an environment abort the refresh recovers from serially, T-1672, not a real regression). That lets the ubuntu Test step be the ONE combined pass/fail + coverage run; the coverage-stamp step no longer re-runs the suite. Raised the ubuntu coverage deadline (7200s) and job timeout (150m) for the memory-capped single run.

Feature (kind=feature): the four TestCoverageFailOnDegraded tests fail at parent (the helper does not exist) and pass at the fix -- red exits non-zero, worker-crash does not, green returns, missing provenance fails closed -- plus the ci.yml once-not-twice wiring assertion. Capability conformance: declared the new fs.read site (cli node, coverage_runner.py) and fs.write site (testsuite, test_coverage_runner.py) in design/frob.strata + the via-ratchet lock, and documented the flag in docs/modules/cli.md.

Trade-off: frob's coverage orchestration captures pytest output to its own log, so a red ubuntu run's failing-test NAMES are not in the job log; the --fail-on-degraded exit + 'suite ran RED' line flag it, reproduce locally for the set. The remaining DEPR006 finding is pre-existing/out-of-scope (T-3739).

### Changed
```
 .github/workflows/ci.yml                           | 41 ++++++++++------
 design/frob.strata                                 |  4 +-
 .../registry/capability-via-ratchet.lock.json      | 12 ++---
 docs/modules/cli.md                                | 15 +++++-
 src/frob/_cli_parsers/_misc.py                     | 10 ++++
 src/frob/app/_config_external.py                   |  2 +
 src/frob/app/config.py                             |  5 ++
 src/frob/app/coverage_runner.py                    | 42 ++++++++++++++++
 tests/test_ci_workflow_matrix.py                   | 48 ++++++++++++++----
 tests/unit/test_coverage_runner.py                 | 57 ++++++++++++++++++++++
 tickets/T-3748/ticket.md                           | 29 ++++++++++-
 11 files changed, 229 insertions(+), 36 deletions(-)
```

### Evidence
- `tests/unit/test_coverage_runner.py::TestCoverageFailOnDegraded::test_red_suite_exits_nonzero` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageFailOnDegraded::test_worker_crash_does_not_fail` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageFailOnDegraded::test_green_suite_returns` (pytest node id, verified passing when recorded)
- `tests/unit/test_coverage_runner.py::TestCoverageFailOnDegraded::test_missing_provenance_fails_closed` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_suite_runs_under_coverage_once_not_twice` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 4343 warning(s), 921 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
