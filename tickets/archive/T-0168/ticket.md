---
id: T-0168
title: TEST001 fires on flow declarations in .strata files -- undefined semantics
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/lang/_walk_strata.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestConventionUnitBinding::test_test001_exempts_strata_flow_declarations
designated_repro_test: null
threat: null
component: null
---
Typani pilot: TEST001 (untested public symbol) fires on flow declarations inside design files, but what a passing test for a design-model flow MEANS is undefined -- frob's own self-model binds no tests to flows either. Decide and implement: either design-file declarations are exempt from TEST001 (their verification is the prover/audit, not pytest -- likely right), or define the discharge semantics precisely. Kill the semantically-confused warning class either way.