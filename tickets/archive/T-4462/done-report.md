## Done report

CI run 34752551520 (Windows leg) reached the post-self-gate steps for the first time and the TEST012 lock-drift step failed in one second with OpenError: under windows-latest's default pwsh shell the step redirected frob check --only test --json to /tmp, which does not exist there. Fix: the step now runs with shell: bash and writes/reads the JSON through a RUNNER_TEMP-derived FROB_TEST_CHECK_PATH environment variable (no shell variable embedded in the python literal). Audit of every step after the self-gate: only TEST012 was unguarded; the T-1366 coverage step is already ubuntu-only; the standalone-install job runs on ubuntu-latest. Evidence: tests/test_ci_workflow_matrix.py::TestPostSelfGateStepsAreWindowsSafe (bash+RUNNER_TEMP on the TEST012 step; no post-self-gate step references /tmp without bash or an OS gate), 45/45 ci-workflow tests pass; YAML validated. Done report re-recorded by the coordinator after the implementer's done-report commit was lost in the rebase (T-4448 shape).

### Changed
```
 .github/workflows/ci.yml         | 18 ++++++++--
 tests/test_ci_workflow_matrix.py | 76 ++++++++++++++++++++++++++++++++++++++++
 tickets/T-4462/ticket.md         |  8 ++---
 3 files changed, 95 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_matrix.py::TestPostSelfGateStepsAreWindowsSafe::test_test012_step_uses_bash_and_runner_temp` (pytest node id, verified passing when recorded)
- `tests/test_ci_workflow_matrix.py::TestPostSelfGateStepsAreWindowsSafe::test_no_post_self_gate_step_references_tmp_without_bash_or_os_gate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 4803 warning(s), 976 waived
- error-findings: none (measured, zero errors)
