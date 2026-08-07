---
id: T-0687
title: 'c++ may-throw analysis: throw sites + callee propagation + noexcept hard-boundary
  obligation'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0662
parent: T-0685
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/lang/**
- tests/unit/test_arch.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/arch.md
  reason: add docs anchor for new frob.arch._cpp_mayraise public symbols (COV001)
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error
- tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_with_catch_all_does_not_fire
- tests/unit/test_arch.py::TestCppMayThrow::test_non_noexcept_function_never_fires
- tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_calling_vector_at_fires_curated_thrower
designated_repro_test: null
acceptance:
- text: GIVEN a noexcept function calling a may-throw callee WHEN the analysis runs
    THEN an error finding names the call site AND a try/catch(...) boundary discharges
    Unknown
  evidence:
  - tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error
  - tests/unit/test_arch.py::TestCppMayThrow::test_noexcept_with_catch_all_does_not_fire
threat: null
component: null
---
Child 2 of T-0685. Same may-set shape over the C++ tree-sitter parse: explicit throw + resolved-callee propagation + std-library thrower table (vector::at, new, stoi, ...). Virtual/indirect/function-pointer calls -> Unknown fail-closed (T-0665's obligation pattern). noexcept functions are HARD boundaries: a may-throw (or Unknown) call inside noexcept is an ERROR finding (std::terminate at runtime), not advisory. Document that full soundness needs libclang eventually; the tree-sitter approximation with fail-closed unknowns is the deliverable.