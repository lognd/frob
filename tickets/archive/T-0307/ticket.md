---
id: T-0307
title: 'capability/test binder: parametrized (and multi-case) tests do not count toward
  TEST001/002/003'
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- src/frob/gates/__init__.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test002_parametrized_test_counts_each_case
- tests/test_gates.py::TestTestGate::test_case_count_direct
designated_repro_test: null
threat: null
component: null
---
FROBLEMS (lograder, aprog-public, feldspar): a frob:tests binding on a @pytest.mark.parametrize'd function satisfies TEST001 but TEST002/TEST003 report 0 collected cases -- collected node id test_x[CMake] does not match the bound function name test_x, so parametrized variants (and proptest!-expanded rust tests) do not count. All three repos worked around it by writing non-parametrized twin tests. Fix: the case counter must map a collected node id back to its bound function by stripping the [param] suffix (and handle rust cargo test list ids), so each param id counts as a case. Add litmus: a parametrized python test + a rust proptest! block each satisfy TEST002/003 for their bound symbol.