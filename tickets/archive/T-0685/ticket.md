---
id: T-0685
title: 'exception may-raise analysis: per-function may-raise sets with fail-closed
  unknowns (parent)'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/gates/**
- docs/design/**
- tests/test_gates.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: scope-add evidence test files covering the T-0685 children's own gate/analysis
    tests, for the parent umbrella's closing evidence
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/unit/test_arch.py
  reason: scope-add evidence test files covering the T-0685 children's own gate/analysis
    tests, for the parent umbrella's closing evidence
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_gates.py::TestFfiBoundaryGate::test_pyo3_drift_fires_ffi001
- tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error
- tests/test_gates.py::TestExhaustiveHandlingGate::test_unknown_without_catch_all_fires_exhaust001
designated_repro_test: null
acceptance:
- text: GIVEN the children closed WHEN frob check runs on a fixture with a known exception
    surface THEN the may-raise sets are queryable and every child gate/advisory fires
    per its own acceptance
  evidence:
  - tests/test_gates.py::TestFfiBoundaryGate::test_pyo3_drift_fires_ffi001
  - tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error
  - tests/test_gates.py::TestExhaustiveHandlingGate::test_unknown_without_catch_all_fires_exhaust001
threat: null
component: null
---
User mandate 2026-07-22: complement the errors-as-values preference with an EXHAUSTIVE static exception story. Compute a per-function may-raise set: explicit raise sites + resolved callees' sets propagated over the call graph + curated builtin-raiser table (dict[k]->KeyError, int()->ValueError, attr->AttributeError, ...). Unresolvable calls (dynamic dispatch, getattr, plugins) contribute an Unknown marker FAIL-CLOSED, per the T-0339 doctrine -- reuse its per-language resolvers (T-0659..T-0664), do not build a second binding analysis. Ubiquitous asynchronous exceptions (MemoryError, KeyboardInterrupt, SystemExit) live in a separate always-possible tier that exhaustiveness never demands enumerated (only a boundary catch-all may discharge). The normalized model's NormalizedRaise/NormalizedCatch events (T-0609..T-0612) are the substrate. Children: Python may-raise resolver, C++ may-throw + noexcept obligation, exhaustive-handling gate + errors-as-values advisory. Umbrella closes when children close.