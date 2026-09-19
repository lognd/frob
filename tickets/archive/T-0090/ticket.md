---
id: T-0090
title: TEST002 misses frob:tests directives bound cross-file to rust symbols
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: moving DOCARCH001 change-narrative out of the test docstring per T-4420
  actor: logan
  at: '2026-09-19'
  old_length: 402
  new_length: 1057
evidence:
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test002_satisfied_by_rust_directive_bound_cross_file
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test002_rust_directive_from_non_test_symbol_does_not_satisfy
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reviewer finding during T-0059: strata-core/src/parse.rs carries 18 frob:tests directives targeting strata-core/src/lib.rs::parse_source, but TEST002 reports 0 unit cases collected for that symbol. Suspect the unit-edge collector does not resolve directives living in a different file than the target symbol (rust cross-file binding). Warn-level today; worth fixing before TEST002 is promoted to error.

DOCARCH001 cleanup note (T-4420): tests/gates_suite/test_test_gate.py::TestTestGate.test_test002_satisfied_by_rust_directive_bound_cross_file's docstring used to say: 'Regression for T-0090: a frob:tests directive living in a different rust file than its target symbol must still count as unit evidence. T-0092 gave rust a real execution-based collector (collect_rust_tests), so this now asserts through the FIRST branch of _valid_edges (real collected node id), not the structural fallback the T-0090 comment used to describe -- .rs was removed from _NATIVE_TEST_EXTENSIONS accordingly.' Moved here; the test docstring now states only what it verifies.