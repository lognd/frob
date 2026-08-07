---
id: T-1033
title: 'python graph walker: widen bare type-alias RHS detection beyond Literal[...]
  (Union/Optional/TypeVar)'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: low
parent: null
tier: ticket
sprint: null
scope:
- src/frob/lang/**
- tests/test_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_lang.py
  reason: T-1033 adds/widens tests in tests/test_lang.py::TestParsePython for the
    widened bare-alias RHS shapes
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_lang.py::TestParsePython::test_bare_widened_alias_rhs_extracted_as_type_symbol
- tests/test_lang.py::TestParsePython::test_bare_unrelated_call_still_unindexed
designated_repro_test: null
threat: null
component: null
---
T-1028 fixed the python symbol walker (src/frob/lang/_walk_python.py) to index type-alias assignments as SymbolKind.TYPE symbols for three shapes: type X = ... (py>=3.12), X: TypeAlias = ..., and bare X = Literal[...] (this repo's own idiom). The bare-RHS detection deliberately stayed narrow to Literal[...] only -- widening _is_literal_alias_rhs's sibling check to also recognize bare X = Union[...], X = Optional[...], and X = TypeVar(...) assignments (common PEP 613-adjacent alias idioms not covered by an explicit TypeAlias annotation) is a separate, deliberate follow-up, not bundled into T-1028's fix.