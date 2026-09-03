## Done report

CI run 33769225680 (windows leg) fired the midrun no-progress watchdog on
test_fleet_status_ticket_readiness_arch001 -- a FALSE stall, not a hang: the
test runs `frob check --only arch` as one subprocess (its own
@pytest.mark.timeout(300)) and reports no pytest call-phase progress for the
subprocess's whole duration. The self-scan-heavy family behaves the same, some
carrying @pytest.mark.timeout(1200). On win32 the Test step runs -p no:xdist
(single-threaded), so those heavy tests run back to back with long
no-progress stretches that are legitimate work.

The 180s midrun threshold was set (T-3689) before a total-budget backstop
existed, to catch cumulative slowness. That job is now done by
FROB_TEST_TOTAL_BUDGET_SECONDS (3000s, T-3740), so the midrun watchdog should
only catch a single test wedged beyond even its own pytest-timeout -- a true
unkillable win32 hang. Raised the threshold 180 -> 1350: above the largest
per-test timeout (1200s) so no legitimately-slow single test false-trips it,
and under the matrix test's existing <1500 Wait-Process-budget assertion so no
test change (and its DUP001 churn) is needed.

Evidence: tests/test_ci_workflow_matrix.py::...test_test_step_sets_frob_test_midrun_watchdog_seconds
asserts the threshold stays inside the step budget; it passes with 1350.
The one remaining repo-wide DEPR006 finding is pre-existing, out of scope, and
tracked by T-3739. This is a CI-config-value change with no code path to
regress at the parent commit, so BUG002 is waived (as in T-3740).

### Changed
```
 .github/workflows/ci.yml | 16 +++++++++++++++-
 tickets/T-3746/ticket.md |  4 +++-
 2 files changed, 18 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_sets_frob_test_midrun_watchdog_seconds` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4311 warning(s), 918 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
