---
id: T-0900
title: Add regression test for COMPLIANCE005 adopted-then-deleted-registry detection
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
- tests/test_gates.py::TestComplianceGate::test_compliance006_fires_on_deleted_registry_after_adoption
- tests/test_gates.py::TestComplianceGate::test_compliance006_silent_on_never_adopted_registry
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-vacuousness sweep), pairs with the
registry-deletion detection fix ticket.

Bind a regression test per affected gate (starting with COMPLIANCE005)
asserting that deleting a previously-present registry file between two
`frob check` runs on the same tree produces a loud violation rather than a
silently clean report, closing the "adopted-then-deleted" gap the paired
fix ticket addresses.