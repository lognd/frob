---
id: T-3785
title: surface win32 full-suite tracebacks in CI to diagnose the doctor cluster
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
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: .github/workflows/ci.yml
  reason: win32 traceback flags
  actor: logan
  at: '2026-09-04'
- op: add
  glob: tests/test_ci_workflow_matrix.py
  reason: possible arg-string assertion update
  actor: logan
  at: '2026-09-04'
body_changes:
- mode: append
  reason: record BUG002 waiver rationale for the CI-config-only diagnostic change
  actor: logan
  at: '2026-09-04'
  old_length: 0
  new_length: 153
evidence:
- tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_surfaces_failure_tracebacks
designated_repro_test: null
evidence_changes:
- old_node: tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_win32_test_step_surfaces_failure_tracebacks
  new_node: tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_surfaces_failure_tracebacks
  reason: T-4265 deleted the diagnostic-step-only test classes and moved this still-valid
    Test-step-mitigation assertion from TestWindowsDiagStepDoesNotGateTheJob into
    the new TestWindowsTestStepMitigationsStayPinned class; same test, same assertion,
    new home
  actor: logan
  at: '2026-09-07'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

frob:waive BUG002 reason="CI-config diagnostic verbosity change (win32 pytest -rA --tb=short); no runtime behavior/repro, no pass/fail semantic change"