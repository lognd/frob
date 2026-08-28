---
id: T-3046
title: 'V-model M6: evidence laundering -- T-3005 and T-3007 landed on parse-test
  evidence that never touches the graph code they added'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/reach.py
- tests/test_graph_reach.py
- scripts/measure_evidence_reach.py
- docs/modules/graph.md
- tests/test_measure_evidence_reach.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/reach.py
  reason: document the new reach() classifier alongside affects()
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_graph_reach.py
  reason: document the new reach() classifier alongside affects()
  actor: logan
  at: '2026-08-26'
- op: add
  glob: scripts/measure_evidence_reach.py
  reason: document the new reach() classifier alongside affects()
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/graph.md
  reason: document the new reach() classifier alongside affects()
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_measure_evidence_reach.py
  reason: unit test for the measurement script main() (TEST001)
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_graph_reach.py::TestClassifyEvidenceReach::test_reaches_via_call_graph_closure
- tests/test_graph_reach.py::TestClassifyEvidenceReach::test_reaches_via_co_located_test_file
- tests/test_graph_reach.py::TestClassifyEvidenceReach::test_does_not_reach_when_closure_misses_scope
- tests/test_graph_reach.py::TestClassifyEvidenceReach::test_unknown_when_test_symbol_unresolved
- tests/test_graph_reach.py::TestClassifyEvidenceReach::test_unknown_when_scope_is_native_only
- tests/test_graph_reach.py::TestClassifyEvidenceReach::test_evidence_scope_alone_does_not_launder_reach
- tests/test_measure_evidence_reach.py::TestMeasureEvidenceReachMain::test_runs_clean_over_a_minimal_ticket_ledger
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f8eff6c8d46411848d68dea686eee4d8d14a5a0c
---
