---
id: T-0526
title: 'frob:debt/frob:todo coherence: paired todo, same-ticket check, symmetric resolution'
state: done
kind: feature
origin: human
created: '2026-07-21'
priority: medium
parent: T-0412
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- tests/unit/graph/test_dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: T-0526 debt/todo coherence needs regression tests in the existing dsl.py
    test file
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/graph/test_dsl.py::TestDebtTodoCoherence::test_unpaired_debt_registers_implicit_todo
- tests/unit/graph/test_dsl.py::TestDebtTodoCoherence::test_explicit_paired_todo_same_ticket_no_implicit_duplicate
- tests/unit/graph/test_dsl.py::TestDebtTodoCoherence::test_mismatched_explicit_todo_is_debt001_shaped_malformed
designated_repro_test: null
threat: null
component: null
---
