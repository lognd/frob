## Done report

Two release-blocking CI fixes, both confined to the ci.yml build job and its
matrix test (T-3740's declared scope: .github/workflows/ci.yml +
tests/test_ci_workflow_matrix.py). Both were latent and surfaced together on
CI run 33748098172 once the win32 hang saga and the flaky-test whack-a-mole
were fixed and the suite ran to completion for the first time.

1. win32 serial-suite budget. The windows Test step runs pytest single-
   threaded (-p no:xdist, a leftover from the hang-diagnostics era). Once the
   suite stopped hanging it ran to completion and its true serial runtime
   exceeded the 1200s FROB_TEST_TOTAL_BUDGET_SECONDS cap while still
   progressing -- nothing wedged (the 180s no-progress watchdog only armed,
   never fired). Raised FROB_TEST_TOTAL_BUDGET_SECONDS 1200->3000, the
   Wait-Process backstop 1500->3300 (kept > the python cap so the diagnostic
   fires first), and the shared job timeout-minutes 60->90. T-3741 tracks
   re-enabling xdist to bring the win32 leg back down.

2. stamp-baseline chunk desync. The T-1366 coverage step chunked
   `frob check --stamp-baseline` by a hand-maintained --only list that had
   drifted to cover only 40 of 68 gate-ids from _stamp_baseline_gate_chunks().
   Because .frob/baseline is stamped only when the accumulated coverage is a
   superset of the expected chunk union, the accumulator never completed, the
   baseline was never written, every command still exited 0, and only the
   step's own assertion caught it (ubuntu+macos both red). Replaced the four
   chunked commands with a single bare `uv run frob check --stamp-baseline`,
   which runs every chunk in one process and always stamps -- desync-proof.

Evidence: tests/test_ci_workflow_matrix.py -- the midrun-watchdog budget test
(asserts the threshold stays inside the raised Wait-Process budget) and the
new test_stamp_baseline_is_bare_not_chunked_by_only (asserts the coverage
step invokes a bare --stamp-baseline and never chunks it by --only). The one
remaining repo-wide DEPR006 finding (frob-deprecated-baseline.lock.json) is
pre-existing, out of this ticket's scope, and tracked separately by T-3739.

### Changed
```
 .github/workflows/ci.yml         | 38 +++++++++++++++++++++++---------------
 tests/test_ci_workflow_matrix.py | 22 ++++++++++++++++++++++
 tickets/T-3740/ticket.md         |  1 +
 3 files changed, 46 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_test_step_sets_frob_test_midrun_watchdog_seconds` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_stamp_baseline_is_bare_not_chunked_by_only` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 4309 warning(s), 918 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
