---
id: T-0901
title: 'Add drift-lock test: every emitted rule= literal must be a _KNOWN_GATE_RULES
  member'
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
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
- tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
- tests/test_gates.py::TestKnownGateRuleIds::test_is_frozenset
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2), pairs with the _KNOWN_GATE_RULES completeness fix ticket.

Add a regression test that statically enumerates every `rule="..."`
literal passed to a `Violation(...)` constructor call across
`src/frob/gates/**` and `src/frob/strata/**` (an AST/regex scan is fine,
mirroring how `_KNOWN_GATE_RULES` itself is a static frozenset) and
asserts it is a subset of `known_gate_rule_ids()` -- so a new gate/rule
added without a matching `_KNOWN_GATE_RULES` entry fails CI immediately
instead of silently reproducing the PARSE001/TICK005/REG011/PII011/
PII012/SYSWAIVE002/THREAT006 omission class.