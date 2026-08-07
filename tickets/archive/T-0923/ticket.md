---
id: T-0923
title: PROTO004 missing from _KNOWN_GATE_RULES (T-0840 listing omission)
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestProtocolOrderingGate::test_call_before_establishing_transition_is_an_ordering_error
- tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id
- tests/test_gates.py::TestKnownGateRuleIds::test_is_frozenset
designated_repro_test: null
threat: null
component: null
---
frob.gates._protocol_summary's protocol_summary_gate emits PROTO004
(T-0840, per-call-site ordering) findings, and TestProtocolOrderingGate
in tests/test_gates.py exercises it, but "PROTO004" was never added to
src/frob/gates/__init__.py's _KNOWN_GATE_RULES frozenset the way PROTO001/
PROTO002/PROTO003 (and now PROTO005, T-0747) were. Concretely: any
`frob:waive PROTO004 reason="..."` anywhere in the tree would be flagged
WAIVE002 (ineffective waiver, unmatchable rule id) even though PROTO004
is a perfectly real, live gate rule -- the same listing-omission class
T-0753 already fixed once for DEAD001. Found while working T-0747
(cleanup obligations), out of that ticket's own scope (T-0747 touches
PROTO005 only). Fix: add "PROTO004" to _KNOWN_GATE_RULES with a comment
citing T-0840, mirroring the PROTO001/002/003/005 entries already there.