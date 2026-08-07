---
id: T-0840
title: path-sensitive per-call-site state verification (ordered call graph)
state: done
kind: feature
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/gates/_protocol_summary.py
- tests/test_gates.py
- tests/test_graph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: 'Evidence tests for T-0840''s PROTO004 ordering check and OrderedCallGraph
    live in tests/test_gates.py and tests/test_graph.py, which need scope-add before
    evidence can bind.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_graph.py
  reason: 'Evidence tests for T-0840''s PROTO004 ordering check and OrderedCallGraph
    live in tests/test_gates.py and tests/test_graph.py, which need scope-add before
    evidence can bind.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestProtocolOrderingGate::test_call_before_establishing_transition_is_an_ordering_error
- tests/test_gates.py::TestProtocolOrderingGate::test_call_after_establishing_transition_is_not_flagged
- tests/test_gates.py::TestProtocolOrderingGate::test_python_with_block_discharges_the_ordering_violation
- tests/test_graph.py::TestCallGraph::test_build_ordered_call_graph_preserves_source_text_call_order
- tests/test_graph.py::TestCallGraph::test_build_ordered_call_graph_resolves_a_rust_private_callee
designated_repro_test: null
threat: null
component: null
---
T-0746 disclosure: PROTO002/PROTO003 (frob.gates._protocol_summary) ask
an EXISTENTIAL question over compute_protocol_summaries' unordered,
per-function transitive requires/transitions sets ("is state S
established by SOME reachable transition anywhere in the tagged
package closure") rather than a path-sensitive one ("is S established
on EVERY path reaching this exact call site"), because the T-0745
engine has no per-call-site statement ordering yet. This is
false-negative-biased (a real ordering violation can be missed if some
other path in the same closure happens to establish the state) -- the
ticket-named crisp case (a state never established by ANY transition
anywhere) is still caught soundly. Building real path-sensitivity needs
an ordered call graph (each function's calls recorded in statement
order, not just as an unordered edge set) plus a per-call-site
dataflow pass over compute_protocol_summaries' SCC-ordered worklist.
Scope: src/frob/graph/**, src/frob/gates/_protocol_summary.py.