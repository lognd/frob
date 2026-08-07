---
id: T-0087
title: python CONST extraction misses call-expression assignments (X = Foo(...))
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_lang.py::TestParsePython::test_module_level_literal_const_extracted
- tests/test_lang.py::TestParsePython::test_module_level_call_expression_const_extracted
designated_repro_test: null
threat: null
component: null
---
UPPER_CASE module constants assigned from a constructor call (TRUST = Lattice(...) in src/frob/strata/_models.py) are not extracted as CONST symbols, so frob:doc/frob:describes edges to them dangle (DRIFT002) and COV001 cannot see them. Found during T-0055.