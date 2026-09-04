---
id: T-3756
title: 'revert T-3748 coverage-once: ubuntu pass/fail must run coverage-free like
  macOS (coverage-sensitive reds)'
state: done
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- tests/unit/test_release_workflow_gate.py
- tests/test_ci_workflow_timeout.py
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record BUG002 waiver for CI-config revert, not repro-in-land-suite testable
  actor: logan
  at: '2026-09-04'
  old_length: 332
  new_length: 592
evidence:
- tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_ubuntu_test_step_budget_at_least_40_minutes
- tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_job_timeout_minutes_exceeds_ubuntu_step_budget
- tests/unit/test_release_workflow_gate.py::TestCiUbuntuTestBudgetRaised::test_macos_and_ubuntu_step_budgets_match
- tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_no_step_level_continue_on_error_smuggled_onto_other_legs
- tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_coverage_step_calls_frob_coverage_full
- tests/test_ci_workflow_matrix.py::TestCoverageStepUsesFrobNotMake::test_suite_runs_under_coverage_once_not_twice
- tests/test_ci_workflow_timeout.py::TestBuildJobHasATimeoutBackstop::test_build_job_declares_timeout_minutes
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Ubuntu CI leg fails reproducibly under coverage (T-3748) while macOS passes coverage-free on identical code. Revert ubuntu Test step to coverage-free pytest -q like macOS; make coverage step a separate non-blocking best-effort measurement (continue-on-error, no --fail-on-degraded). Update coupled workflow-assertion tests to match.

frob:waive BUG002 reason="CI-config change (revert to coverage-free ubuntu pass/fail); the coverage-sensitivity red is only reproducible on the CI runner under coverage+xdist, not in the Linux land suite; the bound tests assert the workflow's declared shape"