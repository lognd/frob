---
id: T-0839
title: 'gates: _merge_canonical_order silently drops violations of gates missing from
  order tuple (hit live via T-0788)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'COV001 requires a frob:doc edge for the new public GateOrderDriftError

    class; docs/modules/gates.md''s Error types section is the existing home

    for this file''s raised/returned error types, so the doc edge must land

    there rather than a new file.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_gates.py::TestGateOrderSetEquality::test_canonical_gate_order_matches_all_gates
- tests/test_gates.py::TestGateOrderSetEquality::test_all_gates_is_subset_of_canonical_order
- tests/test_gates.py::TestGateOrderSetEquality::test_canonical_order_names_no_nonexistent_gate
- tests/test_gates.py::TestMergeCanonicalOrder::test_unknown_gate_key_raises_with_name
- tests/test_gates.py::TestMergeCanonicalOrder::test_all_current_gates_merge_without_raising
designated_repro_test: null
threat: null
component: null
---
Hit live 2026-07-23: T-0788 added the "compliance" gate to _ALL_GATES
but not _CANONICAL_GATE_ORDER; _merge_canonical_order silently DROPS
violations of any gate absent from the order tuple, so COMPLIANCE005
findings would have been invisible in frob check output (zero live loss
only because the gate currently fires nothing). The only detector was
TestGateOrderSetEquality -- red on main but never executed by frob
check's test stage, so main stayed "green" (see T-0756 for that half).

Fix: _merge_canonical_order must fail loudly (raise, listing the missing
gate names) when raw contains a gate not in _CANONICAL_GATE_ORDER --
dropping findings is never acceptable degradation. Add a test proving a
synthetic unknown-gate key raises. Consider deriving the order tuple
membership check from _ALL_GATES at import time so the drift is
impossible to compile, not just caught at runtime.