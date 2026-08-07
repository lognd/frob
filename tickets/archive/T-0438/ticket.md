---
id: T-0438
title: 'gate-order set-equality test: assert set(_CANONICAL_GATE_ORDER) == _ALL_GATES
  so a new gate can''t silently drop from output'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestGateOrderSetEquality::test_canonical_gate_order_matches_all_gates
designated_repro_test: null
threat: null
component: null
---
Filed from the T-0415 review: nothing asserted set(_CANONICAL_GATE_ORDER)
== _ALL_GATES, so a future gate added to one set but not the other could
silently drop from frob check output (the T-0122 swallowed-summary class
that T-0415's post-merge addendum had to fix by hand for the registry gate).