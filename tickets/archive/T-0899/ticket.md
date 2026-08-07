---
id: T-0899
title: 'Add regression gate/test: empty-scope ticket must not silently pass SCOPE001'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestScopePrework::test_scope001_empty_scope_never_returns_bare_empty_tuple_for_a_real_diff
designated_repro_test: null
threat: null
component: null
---
Found while working T-0786 (gate-vacuousness sweep), pairs with the
SCOPE001 empty-scope fix ticket.

Add a regression gate/lint (or extend SCOPE001 itself) that fires loudly
whenever an in-progress/non-queued ticket carries an empty `scope` tuple --
so the "no declared scope" state cannot silently coexist with an active
ticket ever again, whichever fix direction the paired ticket lands. Bind a
test asserting a ticket with scope=() and a non-empty diff produces a
violation instead of `scope_gate` returning `()`.