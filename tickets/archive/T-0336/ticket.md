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
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test001_002_explicit_unit_edge_honored_regardless_of_test_name
designated_repro_test: null
threat: null
component: null
---
Found while working T-0234. gates/__init__.py::_test_edges(snapshot, kind) builds {edge.target: [edges]} (keyed by the TEST id), but _test001_002_one looks up unit_edges.get(record.symref, []) where record.symref is the SOURCE function/method being tested -- these keys can never match. In practice this is invisible whenever the paired test happens to also satisfy the _inferred_unit_cases naming-convention fallback (edges falls back to convention count when the explicit lookup is empty), so most existing frob:tests unit directives silently pass via the convention path instead of the explicit edge they declare. It surfaces as a real TEST001 false-positive for any function whose frob:tests-linked test name does not itself contain the function's snake_case name as a token (observed while adding tests/test_graph.py::TestGeneratedSource for T-0234's is_generated_source). Fix: key _test_edges by edge.src for the unit-kind case (or add a src-keyed variant) so an explicit frob:tests unit edge is honored regardless of test naming.