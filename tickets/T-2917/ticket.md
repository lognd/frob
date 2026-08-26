---
id: T-2917
title: 'CI runs ubuntu-latest only: add windows-latest and macos-latest to the matrix
  so platform regressions are detectable at all'
state: done
kind: bug
origin: human
created: '2026-08-25'
priority: critical
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
  reason: add windows/macos matrix entries
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_ci_workflow_matrix.py
  reason: 'new dedicated test file: assert CI build matrix includes windows-latest
    and macos-latest (T-2917 repro)'
  actor: logan
  at: '2026-08-25'
evidence:
- tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy
- tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_includes_windows_and_macos
- tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_matrix_is_fail_fast_false
designated_repro_test: tests/test_ci_workflow_matrix.py::TestCiBuildMatrixCoversAllThreePlatforms::test_build_job_declares_a_matrix_strategy
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 46cbe8e4d141ea02bac1f8e42309792eb8997984
---
