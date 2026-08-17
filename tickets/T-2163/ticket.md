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
land_commit: null
---
T-2132's own land introduced a line-too-long (E501, 89>88) at src/frob/verify/_quarantine.py:287 -- this is exactly the fleet-blocking finding class T-2132 itself was fixing quarantine raises for (real code finding, correctly gating, but it needs the actual fix, not another dispose). Wrap the offending line.

<!-- frob:no-behavior-change reason="pure line-wrap of raise_quarantine's exempted= assignment (E501, 89>88 chars) -- no logic, control flow, or output changed; the wrapped expression is byte-identical once whitespace is collapsed. Verified via the existing tests/unit/verify/test_quarantine.py suite (15/15 pass, unchanged from before the wrap)." -->

## Done report

Pure formatting fix: wrapped one line in raise_quarantine (E501, 89>88
chars) introduced by T-2132's own land. No behavior change -- verified
via the existing test_quarantine.py suite (15/15 pass, same as before
the wrap). This was blocking the fleet-wide quarantine a second time
with the exact class of finding T-2132 itself said should still gate
(real code, not a clock-driven rule).

### Changed
```
 src/frob/verify/_quarantine.py     |  4 +++-
 tickets/T-2163/ticket.md | 27 +++++++++++++++++++++++++++
 2 files changed, 30 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/verify/test_quarantine.py::TestRaiseQuarantine::test_raises_and_persists` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: AFFECT001@src/frob/verify/_quarantine.py, DUP001@src/frob/verify/_quarantine.py, PRE001@tickets/T-2163, SELFAUDIT001@design, TICK004@tickets.md
