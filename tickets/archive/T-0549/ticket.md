---
id: T-0549
title: 'gates: parametrized no-op tests inflate case counts for edge floors (B7)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: low
parent: T-0403
tier: ticket
sprint: null
scope:
- src/frob/gates/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test002_noop_parametrize_does_not_inflate_case_count
- tests/test_gates.py::TestTestGate::test_case_count_root_none_skips_assertion_check
- tests/test_gates.py::TestTestGate::test_case_count_root_aware_caps_noop_parametrize
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B7. _case_count counts each parametrize expansion as its own case; a parametrize(range(10)) test asserting nothing reports 10 cases, clearing min_unit_cases and inflating TEST003/004/009 blocking-edge floors. Fix direction: only count a parametrize expansion once per (test, symbol) pair for floor purposes, or require an assertion-presence heuristic before crediting a case.