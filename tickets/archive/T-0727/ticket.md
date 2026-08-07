---
id: T-0727
title: 'arch: PythonAdapter never detects class-level annotated fields (_py_class_fields
  gates on a nonexistent expression_statement wrapper)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0329
tier: ticket
sprint: null
scope:
- src/frob/arch/_python.py
- tests/unit/test_arch.py
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets-archive.md
  reason: 'Fixing T-0727''s PythonAdapter bug removed the class-level field parity

    gap that T-0615''s already-archived Done report pinned as a named waiver

    test (test_python_field_detection_is_a_documented_waiver). That test no

    longer exists once T-0727''s fix folds its assertion into

    test_derived_class_has_the_field_and_one_method''s now-4-way parity

    check, so T-0615''s archived evidence list in tickets-archive.md needed

    its stale node id removed to keep COV003 clean. This is a direct,

    in-scope consequence of T-0727''s own fix, not unrelated archive editing.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_derived_class_has_the_field_and_one_method
designated_repro_test: null
acceptance:
- text: GIVEN class Foo with an annotated field WHEN PythonAdapter.adapt runs THEN
    the field appears in NormalizedClass.fields AND the T-0615 waiver test is updated
    to assert parity
  evidence:
  - tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_derived_class_has_the_field_and_one_method
threat: null
component: null
---
Found while working T-0615 (four-way equivalence meta-test). PythonAdapter._py_class_fields (src/frob/arch/_python.py) gates on 'if c.type != "expression_statement": continue' over a class body's named_children, expecting a class-level annotated assignment to be wrapped in an expression_statement node. In practice tree-sitter-python's grammar yields the assignment node directly as a named child of the class block, with NO expression_statement wrapper. Concrete repro: PythonAdapter().adapt(...) on 'class Foo:\n    x: int = 0\n' returns classes[0].fields == [] every time -- confirmed directly against the adapter, not just inferred. No existing test caught this because TestPythonAdapter's real-fixture tests never assert on .fields via the adapter itself (only a hand-built NormalizedField construction test exists, bypassing the adapter). T-0615's tests/unit/test_arch.py::TestFourWayCrossLanguageEquivalence::test_python_field_detection_is_a_documented_waiver currently PINS this broken behavior as a documented waiver (asserting derived.fields == []) -- fixing this ticket must also update/remove that waiver test to assert real parity with TS/rust/kotlin (which all capture this shape via their own adapters).