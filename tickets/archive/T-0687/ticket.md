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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/**
- src/frob/lang/**
- tests/unit/test_arch.py
- docs/modules/arch.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/arch.md
  reason: add docs anchor for new frob.arch._cpp_mayraise public symbols (COV001)
  actor: logan
  at: '2026-07-27'
body_changes:
- mode: append
  reason: condense error-severity scope-carveout rationale into T-0687 body
  actor: logan
  at: '2026-09-19'
  old_length: 547
  new_length: 1570
evidence:
- tests/unit/arch_suite/test_misc.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error
- tests/unit/arch_suite/test_misc.py::TestCppMayThrow::test_noexcept_with_catch_all_does_not_fire
- tests/unit/arch_suite/test_misc.py::TestCppMayThrow::test_non_noexcept_function_never_fires
- tests/unit/arch_suite/test_misc.py::TestCppMayThrow::test_noexcept_calling_vector_at_fires_curated_thrower
designated_repro_test: null
acceptance:
- text: GIVEN a noexcept function calling a may-throw callee WHEN the analysis runs
    THEN an error finding names the call site AND a try/catch(...) boundary discharges
    Unknown
  evidence:
  - tests/unit/arch_suite/test_misc.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error
  - tests/unit/arch_suite/test_misc.py::TestCppMayThrow::test_noexcept_with_catch_all_does_not_fire
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child 2 of T-0685. Same may-set shape over the C++ tree-sitter parse: explicit throw + resolved-callee propagation + std-library thrower table (vector::at, new, stoi, ...). Virtual/indirect/function-pointer calls -> Unknown fail-closed (T-0665's obligation pattern). noexcept functions are HARD boundaries: a may-throw (or Unknown) call inside noexcept is an ERROR finding (std::terminate at runtime), not advisory. Document that full soundness needs libclang eventually; the tree-sitter approximation with fail-closed unknowns is the deliverable.

<!-- narrative-moved:src/frob/arch/_models.py:206:T-0687 -->
: T-0687 added `"error"` (previously `warning`/`suggestion`/`info` were
: the entire set) for a hard-boundary violation category
: (`"cpp-noexcept-throws"`) whose
: severity is not advisory -- an escaping exception from a `noexcept`
: function is `std::terminate` at runtime, not a recoverable condition a
: caller can choose to act on later. Promoting `"error"`-severity
: `ArchSuggestion`s into an enforced, unwaivable gate finding (the way
: `frob.gates._unwaivable_channel_rules` already does for every OTHER
: `ArchCategory`) is `src/frob/gates/**` wiring, out of T-0687's own
: declared scope (`src/frob/arch/**`/`src/frob/lang/**`/
: `tests/unit/test_arch.py` alone) -- filed as a follow-up, same T-0728
: "built and tested first, dispatch wiring landed later" precedent
: `frob.arch._exceptions.check_errors_as_values`'s own module docstring
: already establishes for exactly this class of scope carve-out.
frob:doc docs/modules/arch.md#arch-suggestion