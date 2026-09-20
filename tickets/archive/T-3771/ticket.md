---
id: T-3771
title: Add regression test for win32 pytest --timeout=600
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
- tests/test_ci_workflow_matrix.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_raises_per_test_timeout_to_600
designated_repro_test: null
evidence_changes:
- old_node: tests/test_ci_workflow_matrix.py::TestWindowsDiagStepDoesNotGateTheJob::test_win32_test_step_raises_per_test_timeout_to_600
  new_node: tests/test_ci_workflow_matrix.py::TestWindowsTestStepMitigationsStayPinned::test_win32_test_step_raises_per_test_timeout_to_600
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
T-3757 landed the win32 --timeout=600 fix in .github/workflows/ci.yml with cmd: evidence, which COV003 rejects for non-docs/ux kinds. Add a node-id test asserting the windows Test step's pytest invocation includes --timeout=600, to be used as evidence for both this ticket and rebinding T-3757.