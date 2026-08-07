---
id: T-0548
title: 'gates: TEST001 credit requires real coverage, not name-match only (B1)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: high
parent: T-0403
tier: ticket
sprint: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTest015VacuousCredit::test_fires_on_no_op_test_body
- tests/test_gates.py::TestTest015VacuousCredit::test_silent_when_any_matching_test_asserts
- tests/test_gates.py::TestTest015VacuousCredit::test_silent_when_no_test_matches_at_all
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B1/E1. TEST001 (the only blocking per-symbol test gate) is satisfied by a single collected pytest node id whose name contains the function's snake name (_inferred_unit_cases, or a frob:tests edge that merely collects). Nothing inspects assertions or whether the symbol is even called: def test_myfunc(): pass clears it. TEST002 (case count) and TEST005 (branch coverage) are WARN-only so they never block. Repro: name an empty test after a public function -> frob check green. RIGHT-WAY fix direction: tie TEST001 credit to nonzero per-symbol branch coverage (promote TEST005 to ERROR, or require both name/edge match AND coverage>0 before TEST001 clears). Large, cross-cutting change (touches TEST002/003/004/005/009 severity + interaction, and the legacy-adoption WARN campaign noted in frob.toml comments) -- too large for the T-0403 sweep budget, needs its own dedicated ticket.