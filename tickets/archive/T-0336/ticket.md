---
id: T-0336
title: TEST001/TEST002 _test_edges keyed by target, not src -- explicit frob:tests
  unit edges never match record.symref lookup
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: moving DOCARCH001 change-narrative out of the test docstring per T-4420
  actor: logan
  at: '2026-09-19'
  old_length: 1036
  new_length: 2220
evidence:
- tests/gates_suite/test_test_gate.py::TestTestGate::test_test001_002_explicit_unit_edge_honored_regardless_of_test_name
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-0234. gates/__init__.py::_test_edges(snapshot, kind) builds {edge.target: [edges]} (keyed by the TEST id), but _test001_002_one looks up unit_edges.get(record.symref, []) where record.symref is the SOURCE function/method being tested -- these keys can never match. In practice this is invisible whenever the paired test happens to also satisfy the _inferred_unit_cases naming-convention fallback (edges falls back to convention count when the explicit lookup is empty), so most existing frob:tests unit directives silently pass via the convention path instead of the explicit edge they declare. It surfaces as a real TEST001 false-positive for any function whose frob:tests-linked test name does not itself contain the function's snake_case name as a token (observed while adding tests/test_graph.py::TestGeneratedSource for T-0234's is_generated_source). Fix: key _test_edges by edge.src for the unit-kind case (or add a src-keyed variant) so an explicit frob:tests unit edge is honored regardless of test naming.

DOCARCH001 cleanup note (T-4420): tests/gates_suite/test_test_gate.py::TestTestGate.test_test001_002_explicit_unit_edge_honored_regardless_of_test_name's docstring used to say: 'Regression for T-0336 (root-caused while adding tests/test_graph.py::TestGeneratedSource for T-0234's is_generated_source): _test_edges used to index unit TESTS edges by edge.target only, but the directive convention used throughout this codebase for written directly above the source function, naming its covering test (docs/modules/testing.md) binds src to the source symbol and target to the test id -- record.symref (the source) can then only ever match edge.src, never edge.target, so a target-only index can structurally never find it. zebra_helper is deliberately tested by test_alpha_omega_case, a name that shares no token with zebra_helper -- _inferred_unit_cases naming-convention fallback cannot match it, so TEST001/002 can only stay clean here via the explicit frob:tests ... kind=unit edge being both found (_unit_test_edges indexing edge.src) and honored as real execution evidence (_valid_edges checking edge.target too).' Moved here; the test docstring now states only what it verifies.