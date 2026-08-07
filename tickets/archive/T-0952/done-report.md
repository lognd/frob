## Done report

Tarjan's _strongconnect recursed natively and raised RecursionError on long dependency chains (reproduced at ~1000 nodes by T-0950). Rewritten iteratively with an explicit (node, neighbor-iterator) frame stack; neighbor consumption order and component pop points preserved, so output ordering is unchanged (all 7 pre-existing tests pass unmodified). Three regression tests cover the documented pre-fix repro, a 5000-node chain, and the same chain closed into one SCC.

### Changed
```
 src/frob/cycle/graph.py  | 55 +++++++++++++++++++++++++++++---------
 tests/unit/test_cycle.py | 69 ++++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md               | 46 +++++++++++++++++++++++++++++++-
 3 files changed, 156 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_cycle.py::test_no_cycle` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle.py::test_add_node_and_nodes_and_neighbors` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle.py::test_simple_cycle` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle.py::test_three_node_cycle` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle.py::test_two_independent_cycles` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle.py::test_self_loop` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle.py::test_cycle_not_duplicated` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle.py::test_long_chain_would_have_crashed_recursive_tarjan` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle.py::test_long_chain_no_recursion_error` (pytest node id, verified passing when recorded)
- `tests/unit/test_cycle.py::test_long_chain_with_cycle_no_recursion_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
