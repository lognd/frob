## Done report

The T-1366 coverage-stamp step ran `frob coverage --full` -- the full test
suite a SECOND time, under coverage instrumentation -- on all three OS with no
if: gating. This duplicated the Test step's own suite run on every leg, and on
windows piled a coverage-instrumented suite onto the already-serial (-p
no:xdist) long pole. Coverage is platform-independent (the committed
frob-coverage.lock.json is a single Linux baseline; reconcile/doctor/stamp-
baseline are repo-state), so the whole step belongs on one leg.

Fix: gate the step to `if: matrix.os == 'ubuntu-latest'`, and cap the coverage
xdist pool via FROB_COVERAGE_MAX_WORKERS=2. The pool sizes itself at 1536
MiB/worker (_DEFAULT_PER_WORKER_MEM_MB), which gave -n 4 on the 16 GB / 4-core
runner -- but a coverage-instrumented worker with the native extensions loaded
exceeds that, so a worker was OOM-killed (T-1672 signature) and the run fell
back to the ~2x-slower serial retry. Two workers fit available RAM and keep
the run parallel.

Evidence: tests/test_ci_workflow_matrix.py::...test_coverage_step_is_gated_to_ubuntu_only
asserts the step carries the ubuntu-only if: gate. T-3748 tracks the deeper
reuse (run the suite once WITH --cov in the Test step and stamp from that,
eliminating the second full run entirely). The one remaining repo-wide DEPR006
finding is pre-existing, out of scope, tracked by T-3739. CI-config change with
no code path to regress at parent, so BUG002 is waived (as in T-3740/T-3746).

### Changed
```
 .github/workflows/ci.yml         | 20 ++++++++++++++++++++
 tests/test_ci_workflow_matrix.py | 20 ++++++++++++++++++++
 tickets/T-3747/ticket.md         |  6 +++++-
 3 files changed, 45 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_is_gated_to_ubuntu_only` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 1 error(s), 4306 warning(s), 918 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
