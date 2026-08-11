---
id: T-2163
title: E501 in _quarantine.py (T-2132 land) re-raises the fleet quarantine
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/_quarantine.py
evidence_scope:
- tests/unit/verify/test_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_raises_and_persists
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2132's own land introduced a line-too-long (E501, 89>88) at src/frob/verify/_quarantine.py:287 -- this is exactly the fleet-blocking finding class T-2132 itself was fixing quarantine raises for (real code finding, correctly gating, but it needs the actual fix, not another dispose). Wrap the offending line.

<!-- frob:no-behavior-change reason="pure line-wrap of raise_quarantine's exempted= assignment (E501, 89>88 chars) -- no logic, control flow, or output changed; the wrapped expression is byte-identical once whitespace is collapsed. Verified via the existing tests/unit/verify/test_quarantine.py suite (15/15 pass, unchanged from before the wrap)." -->