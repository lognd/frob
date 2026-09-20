## Done report

T-3748 changed the ubuntu Test step from 'timeout -s ABRT 40m uv run pytest -q' to 'timeout -s ABRT 130m uv run frob coverage --full --fail-on-degraded' (the suite now runs once under coverage) and raised the build job timeout to 150m. Four workflow-assertion tests still encoded the old form and failed on EVERY platform (they parse ci.yml, not the OS), which is why run 33831015243's macOS+ubuntu legs went red: test_build_job_declares_timeout_minutes asserted timeout<=120 (now 150); three TestCiUbuntuTestBudgetRaised tests regex'd 'uv run pytest -q' for the ubuntu step (now the coverage form) and asserted mac==ubuntu budget parity (T-3748 intentionally diverged them). Fixes: raise the ceiling to 180; regex the coverage form; reframe the parity invariant to ubuntu>=mac (ubuntu does the combined coverage+test run), both above the 40m floor. Evidence: the four updated tests pass. DEPR006 is pre-existing/out-of-scope (T-3739).

### Changed
```
 tests/test_ci_workflow_timeout.py        | 10 ++++---
 tests/unit/test_release_workflow_gate.py | 48 +++++++++++++++++++++++---------
 tickets/T-3750/ticket.md                 |  7 ++++-
 3 files changed, 47 insertions(+), 18 deletions(-)
```

### Evidence
- `tests/test_ci_workflow_timeout.py::TestBuildJobHasATimeoutBackstop::test_build_job_declares_timeout_minutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_ubuntu_test_step_budget_at_least_40_minutes` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_job_timeout_minutes_exceeds_ubuntu_step_budget` (pytest node id, verified passing when recorded)
- `tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_macos_and_ubuntu_step_budgets_match` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 4311 warning(s), 918 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
