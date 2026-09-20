## Done report

Scope note: this lands only acceptance [3] (the gate step actually runs
on windows even when Test fails) -- the smallest change that decouples
the gate from the Test step's outcome. Acceptance [1]/[2] (per-test/
per-file time decomposition of the 57-minute windows Test step, and a
fix addressing that measured cause) are explicitly deferred, per
direct dispatch instruction, and are NOT closed by this land -- the
step-duration/budget-margin problem this ticket also describes is
still open. Filing a follow-up ticket to carry [1]/[2] forward so they
are not silently dropped.

Evidence: tests/test_ci_workflow_matrix.py::TestSelfGateRunsOnWindowsEvenIfTestStepFails::test_self_gate_step_runs_on_windows_after_a_prior_failure
(pytest node id bound via `frob ticket evidence`, accepts criterion 3).
Verified locally: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`
parses cleanly; the new test passes under `uv run pytest
tests/test_ci_workflow_matrix.py -x -q` (19 passed). Windows itself
cannot be run from this host, so the actual on-runner behavior change
(self-gate step executing after a failing windows Test step) is
unverified until the next real Windows CI run -- this is a workflow-
correctness change, not a repro of the CI failure.
Filed: T-4372 "Windows CI Test step time budget: measure
per-test/per-file duration and fix the measured cause" (acceptance
[1]/[2] carried forward).
Gates: uv run frob check --ticket T-4269 (to be run before land)

### Changed
```
 .github/workflows/ci.yml           | 11 +++++++++++
 tests/test_ci_workflow_matrix.py   | 34 ++++++++++++++++++++++++++++++++++
 tickets/T-4269/ticket.md           |  5 ++++-
 tickets/T-4372/ticket.md | 30 ++++++++++++++++++++++++++++++
 4 files changed, 79 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestSelfGateRunsOnWindowsEvenIfTestStepFails::test_self_gate_step_runs_on_windows_after_a_prior_failure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 0 error(s), 4769 warning(s), 969 waived
- error-findings: none (measured, zero errors)
