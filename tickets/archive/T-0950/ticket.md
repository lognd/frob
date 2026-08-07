---
id: T-0950
title: investigate frob.cycle's Tarjan SCC as a rust-candidate, sized against real
  repo-scale graphs
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: T-0927
tier: ticket
sprint: null
scope:
- src/frob/cycle/**
- docs/audits/check-performance.md
- tests/unit/test_cycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/audits/check-performance.md
  reason: 'sizing finding for this ticket must be recorded in the audit doc that filed
    it (docs/audits/check-performance.md), per T-0930''s own precedent scope addition
    for the same doc.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_cycle.py
  reason: 'binding this ticket''s evidence to the existing cycle test suite (tests/unit/test_cycle.py),
    confirming find_cycles behavior is unchanged after the sizing investigation (no
    code shipped, but evidence must resolve against real tests).

    '
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
designated_repro_test: null
threat: null
component: null
---
Found while working T-0930 (rust-candidate row migration off the
frob-check-performance audit, docs/audits/check-performance.md). T-0930
investigated dead_symbols (row 8) as its rust-candidate and found that
neither the batched resolve-edges matching loop nor the per-symbol
token-scan helpers actually win in Rust at this repo's real per-package
data scale (PyO3 marshaling overhead exceeds the loop-speed win; see
the audit doc's T-0930 remediation log for the measured numbers).

frob.cycle.graph's Tarjan SCC (find_cycles/_TarjanState._strongconnect,
src/frob/cycle/graph.py) is a plausible different rust-candidate: pure
algorithm over a DependencyGraph of plain string node names, no
tree-sitter Node objects at all, the same clean data-in/data-out shape
frob_core's existing kernels already use. It was NOT sized against real
repo-scale import graphs this pass (part of the audit's "static" bucket,
lumped with dup/arch/bind/exports at 22.9s total, no per-tool
breakdown). Investigate: measure find_cycles' own share of the static
bucket's wall time in isolation (bypass the thread-pool the same way
T-0930 bypassed the process-pool for dead_symbols), and only port to
frob_core if the measured share is large enough, and the graph volumes
involved are large enough, that PyO3's per-call marshaling tax would
plausibly amortize (T-0930's dead_symbols finding suggests this
threshold is higher than "one call per gate run" -- confirm before
porting, do not assume the algorithm-simplicity argument alone justifies
a port).