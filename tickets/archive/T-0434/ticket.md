---
id: T-0434
title: G4/G9 frob.lang audit findings (out of graph/ scope, T-0402 residual)
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0402
tier: ticket
sprint: null
scope:
- src/frob/lang/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_lang.py::TestErrors::test_syntax_error_logs_partial_tree_warning
- tests/test_lang.py::TestParsePython::test_directive_binds_across_two_blank_lines
designated_repro_test: null
threat: null
component: null
---
Residual from T-0402 graph audit (docs/audits/graph.md): G4 and G9 live in frob.lang (parse_file API / partial-parse handling), out of the graph/ scope of T-0402. See docs/audits/graph.md G4/G9 for the specific findings.