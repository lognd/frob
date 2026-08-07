---
id: T-0895
title: Add regression test for dup_gate native-unavailable loud-violation behavior
state: done
kind: bug
origin: human
created: '2026-07-23'
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
- tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2), pairs with the dup_gate native-unavailable fix ticket.

Add a regression test asserting that `dup_gate` with `[dup].enforce=true`
and a mocked/forced `core_available() == False` produces a real Violation
(not just a log line), closing the "opted-in enforcement silently no-ops
when the native toolchain is missing" gap the paired fix ticket addresses.