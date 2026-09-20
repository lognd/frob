## Done report

The win32 Test step ran -p no:xdist -v --full-trace, T-3549/T-3560 diagnostics-era artifacts from the hang investigation. Single-threaded, the collection-heavy 13k-test suite crawled so badly that on run 33778211294 the midrun watchdog false-fired from session start with zero test call-phase progress. All win32 hang root causes are fixed (T-3686/3708/3726/3730/3735/3738) and FROB_TEST_IGNORE_CONSOLE_CTRL neutralizes the injected-SIGINT class that -p no:xdist was introduced to dodge, so the leg now runs parallel via pyproject's -n auto --dist=loadgroup addopts like ubuntu/macos. Dropped the diagnostic flags, kept -q. Pushed in isolation to read the win32 result cleanly (ubuntu still fails on coverage, handled separately by T-3748). Evidence: the matrix midrun-watchdog test exercises the win32 Test step. DEPR006 is pre-existing/out-of-scope (T-3739). CI-config change, BUG002 waived (as T-3740/3746/3747).

### Changed
```
 .github/workflows/ci.yml | 13 ++++++++++++-
 tickets/T-3741/ticket.md |  6 +++++-
 2 files changed, 17 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_sets_frob_test_midrun_watchdog_seconds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4307 warning(s), 918 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
