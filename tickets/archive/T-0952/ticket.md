---
id: T-0952
title: 'cycle: Tarjan find_cycles recurses natively, RecursionError on long chains'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/cycle/**
- tests/unit/test_cycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_cycle.py
  reason: regression test for the iterative Tarjan rewrite
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_cycle.py::test_no_cycle
- tests/unit/test_cycle.py::test_add_node_and_nodes_and_neighbors
- tests/unit/test_cycle.py::test_simple_cycle
- tests/unit/test_cycle.py::test_three_node_cycle
- tests/unit/test_cycle.py::test_two_independent_cycles
- tests/unit/test_cycle.py::test_self_loop
- tests/unit/test_cycle.py::test_cycle_not_duplicated
- tests/unit/test_cycle.py::test_long_chain_would_have_crashed_recursive_tarjan
- tests/unit/test_cycle.py::test_long_chain_no_recursion_error
- tests/unit/test_cycle.py::test_long_chain_with_cycle_no_recursion_error
designated_repro_test: null
threat: null
component: null
---
Found while working T-0950 (sizing frob.cycle's Tarjan SCC as a
rust-candidate). `_TarjanState._strongconnect` (src/frob/cycle/graph.py)
is implemented as native Python recursion, one stack frame per DFS edge
traversed. A synthetic stress graph of 1000 nodes / 3000 random edges
raised `RecursionError: maximum recursion depth exceeded` (default
sys.getrecursionlimit()=1000) partway through `find_cycles`, well below
any dramatic scale -- a real long import chain (or a pathological
generated-code project) could hit this in production. Convert
`_strongconnect` to an explicit-stack (iterative) Tarjan formulation, or
raise/manage the recursion limit deliberately with a documented ceiling,
so `find_cycles` cannot crash on a graph shaped like a long chain rather
than a wide fan-out. Not fixed under T-0950 itself -- that ticket's scope
was sizing a rust-candidate decision, not correctness -- but the crash is
real and reproducible with a small synthetic script, not a hypothetical.