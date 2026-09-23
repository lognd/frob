---
id: T-5294
title: TEST002/3/4/7/9 test-gate detectors miscount/misfire on real fixtures
state: done
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/gates_suite/test_test_gate.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates
  reason: narrow the directory lease to the touched file so T-5274/T-5275 can start
  actor: logan
  at: '2026-09-22'
- op: add
  glob: src/frob/gates/__init__.py
  reason: narrow the directory lease to the touched file so T-5274/T-5275 can start
  actor: logan
  at: '2026-09-22'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
evidence:
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test003_satisfied_by_parametrized_case_with_dot_in_case_id
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test003_satisfied_by_parametrized_test_node_id
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test004_passes_with_enough_e2e
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test002_parametrized_test_counts_each_case
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test003_satisfied_by_proptest_macro_block
- tests/gates_suite/test_test_gate.py::TestConventionUnitBinding::test_test009_satisfied_by_e2e_edge
- tests/gates_suite/test_test_gate.py::TestPairLevelIntegration::test_test007_passes_when_boundary_tested
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5294
branch: t-5294
---
gh run 35717833933; re-verified on dev tip 3acf8c6b30: 7 failures in tests/gates_suite/test_test_gate.py -- test_test003_satisfied_by_parametrized_case_with_dot_in_case_id, test_test003_satisfied_by_parametrized_test_node_id, test_test004_passes_with_enough_e2e, test_test002_parametrized_test_counts_each_case, test_test003_satisfied_by_proptest_macro_block, test_test009_satisfied_by_e2e_edge, test_test007_passes_when_boundary_tested. All are 'expected pass, gate still flags' shape -- detector regressions, not fixture drift.