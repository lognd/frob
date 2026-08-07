---
id: T-0090
title: TEST002 misses frob:tests directives bound cross-file to rust symbols
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestTestGate::test_test002_satisfied_by_rust_directive_bound_cross_file
- tests/test_gates.py::TestTestGate::test_test002_rust_directive_from_non_test_symbol_does_not_satisfy
designated_repro_test: null
threat: null
component: null
---
Reviewer finding during T-0059: strata-core/src/parse.rs carries 18 frob:tests directives targeting strata-core/src/lib.rs::parse_source, but TEST002 reports 0 unit cases collected for that symbol. Suspect the unit-edge collector does not resolve directives living in a different file than the target symbol (rust cross-file binding). Warn-level today; worth fixing before TEST002 is promoted to error.