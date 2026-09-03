## Done report

Run 33804740730 validated T-3741's win32 xdist re-enable: the log showed live execnet worker threads (Thread-1 run_server, run_connection x N) and F./. test progress with NO KeyboardInterrupt saga -- the console-ctrl mitigation held. But the suite hit SUITE-RESULT: TOTAL-BUDGET-EXCEEDED at 3001.1s: even parallel, the 13k-test suite on a 4-core windows runner (subprocess spawn ~2x macos, whose xdist suite is ~25min) runs past the 3000s FROB_TEST_TOTAL_BUDGET_SECONDS cap. Raised the total budget 3000->4500s and the outer Wait-Process backstop 3300->4800s; the job timeout is already 150m (T-3748) and covers it. The 1350s midrun watchdog (T-3746) and pytest-timeout still catch a genuine per-test hang, so this is a measured raise. Evidence: the midrun-watchdog matrix test exercises the win32 Test step env. CI-config value change, BUG002 waived (as T-3740/3741/3746/3747). DEPR006 is pre-existing/out-of-scope (T-3739).

### Changed
```
 .github/workflows/ci.yml | 20 ++++++++++++--------
 tickets/T-3749/ticket.md |  6 +++++-
 2 files changed, 17 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_sets_frob_test_midrun_watchdog_seconds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4311 warning(s), 918 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
