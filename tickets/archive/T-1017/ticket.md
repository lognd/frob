---
id: T-1017
title: 'hotfix: SCOPE002 gate function over ARCH001 threshold + callgraph E501 (own-gate
  fallout from T-0998 land)'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/graph/callgraph.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestScope002ClosureGate::test_warns_on_unscoped_doc_target
- tests/test_graph.py::TestScopePrivateHelperGaps::test_flags_scoped_caller_of_unscoped_private_helper
designated_repro_test: null
threat: null
component: null
---
T-0998 landed _scope002_violations at 84 lines and one 89-char line in callgraph.py; both now error-tier under our own promotions. Extracted _scope002_edge_gap_violations/_scope002_helper_gap_violations/_scope002_add_hint (also killing the 4x-duplicated message body) and wrapped the long line. All 19 scope-closure tests green post-refactor.