---
id: T-0293
title: evidence recording must normalize/reject Class.method vs Class::method separator
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/gates/__init__.py
- src/frob/testing/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_tickets.py::TestEvidenceValidation::test_validate_evidence_normalizes_dot_separator_to_double_colon
- tests/test_tickets.py::TestEvidenceValidation::test_validate_evidence_normalizes_dot_with_parametrized_suffix
- tests/test_tickets.py::TestEvidenceValidation::test_add_evidence_normalizes_dot_form_before_resolving_and_storing
designated_repro_test: null
acceptance:
- text: given evidence recorded as file::Class.method (dot before method), when it
    is stored, then it is either normalized to the canonical pytest file::Class::method
    form or rejected at record time with a clear message -- never silently stored
    to fail COV003 downstream
  evidence: []
- text: 'given the canonical :: form, when resolved against collected node ids, then
    it matches (regression: the T-0282/T-0217 dot-form evidence that slipped past)'
  evidence: []
threat: null
component: null
---
Bit twice (2026-07-19): T-0282 and T-0217 both had evidence stored as tests/...py::Class.method with a DOT between class and method, which never resolves against pytest node ids (Class::method) and surfaces only as a late, confusing COV003 at check time. The recording path (frob ticket evidence / Done-report evidence capture) must canonicalize to :: (or reject) at write time. Cheapest sound fix: normalize a single-dot-before-final-segment in a ::-qualified test id to ::, OR validate against the collected manifest at record time and refuse an unresolvable id. Pairs with T-0292 (COV003 hint bug) -- same gate, both about making COV003 failures self-explanatory and hard to create.