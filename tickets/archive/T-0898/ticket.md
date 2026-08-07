---
id: T-0898
title: Add regression tests for RENDER001/PII010 loud-on-unparseable-file behavior
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_render_lint.py
- src/frob/gates/_pii_structural.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestRenderLintGate::test_unparseable_file_fires_parse001
- tests/test_gates.py::TestPiiStructuralCrossLanguage::test_unparseable_python_file_fires_parse001
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-by-gate vacuous-satisfaction sweep, round
2), pairs with the private-ast.parse-silent-skip fix ticket.

Add a regression test per affected gate (RENDER001, PII010/SEC110 at
minimum) asserting a syntactically-broken fixture file produces a loud
finding (a PARSE001-shaped violation, or the gate's own equivalent)
instead of a silent zero-violation pass, closing the private-parse-path
silent-skip gap the paired fix ticket addresses.