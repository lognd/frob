---
id: T-0275
title: 'fix(gates): TEST001/TEST003 evidence match must accept parametrized pytest
  node ids'
state: done
kind: bug
origin: agent
created: '2026-07-18'
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
- tests/test_gates.py::TestTestGate::test_test003_satisfied_by_parametrized_test_node_id
- tests/test_gates.py::TestTestGate::test_node_id_collected_direct
designated_repro_test: null
threat: null
component: null
---
Coordinator-reported bug (Bug B): a `# frob:tests ...` comment placed
directly above a `@pytest.mark.parametrize(...)`-decorated test was
reported as silently unbound (feldspar FROBLEMS.md 2026-07-18,
`test_library_thermo.py`), while the identical comment above an
undecorated `def` bound fine -- hypothesized as a decorator-attachment
bug in the comment-to-symbol binder.