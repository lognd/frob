---
id: T-2205
title: 'verify_imports has zero consumers now that its blocker landed: T-2188 shipped
  the opt-in, T-2195 fixed the primitive, and nothing tracks turning it on for COV006/DEAD001/PROTO001-005'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
blocked_by:
- T-2211
- T-2211
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_protocol_summary.py
- tests/test_gates.py
evidence_scope:
- tests/test_graph.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: repro + evidence test for verify_imports=True wiring into dead_symbol_gate
  actor: logan
  at: '2026-08-16'
evidence:
- tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry
- tests/test_gates.py::TestDeadSymbolGate::test_dead_symbol_gate_verifies_imports_across_a_same_named_collision
designated_repro_test: tests/test_gates.py::TestDeadSymbolGate::test_dead_symbol_gate_verifies_imports_across_a_same_named_collision
acceptance:
- text: 'Measured: ''git grep verify_imports=True -- src/'' returns only a docstring
    line (src/frob/graph/callgraph.py:397). No production caller opts in, and no open
    ticket tracked the wiring -- T-2188 (which added the flag) and T-2195 (which fixed
    the primitive it depends on) are both state=done. So the capability is proven,
    unblocked, and reaches nothing. This test MUST fail against current main: at least
    one consumer must pass verify_imports=True.'
  evidence:
  - tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry
- text: RE-MEASURE the blast radius before wiring anything. The only numbers we have
    -- DEAD001 46 -> 241 and COV006 30 -> 622 -- were taken while resolve_local_import
    returned None for every intra-repo import, i.e. with zero cross-file edges resolving.
    T-2195 (808e0c6fb3f4) changed that completely, so those figures are obsolete and
    almost certainly wrong in both magnitude and direction. Report the new per-gate
    delta and JUDGE each appearing/disappearing finding; a count with no per-finding
    judgement is not evidence.
  evidence:
  - tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry
- text: Wire consumers ONE AT A TIME with its own measurement, do not flip all three
    together. DEAD001's failure direction is reporting LIVE symbols as dead, which
    is silent and destructive; COV006's is marking uncovered code covered. Preserve
    scope_private_helper_gaps' documented verify_imports=False opt-out (T-0998/T-1012
    -- it keys on directory co-location, not import reachability). And per the epic's
    own item 3, fail CLOSED (report UNRESOLVED, T-1664) where import resolution genuinely
    cannot decide, rather than guessing in either direction.
  evidence:
  - tests/test_graph.py::TestCallGraph::test_build_reference_graph_catches_dispatch_table_entry
threat: null
component: null
anchor: false
anchor_reason: null
---
