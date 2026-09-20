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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/arch/**
- src/frob/gates/**
- docs/design/**
- tests/test_gates.py
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
body_changes:
- mode: append
  reason: condense builtin-raiser table rationale into T-0686 body
  actor: logan
  at: '2026-09-19'
  old_length: 1010
  new_length: 1902
evidence:
- tests/gates_suite/test_compliance.py::TestFfiBoundaryGate::test_pyo3_drift_fires_ffi001
- tests/unit/arch_suite/test_misc.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error
- tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate::test_unknown_without_catch_all_fires_exhaust001
designated_repro_test: null
acceptance:
- text: GIVEN the children closed WHEN frob check runs on a fixture with a known exception
    surface THEN the may-raise sets are queryable and every child gate/advisory fires
    per its own acceptance
  evidence:
  - tests/gates_suite/test_compliance.py::TestFfiBoundaryGate::test_pyo3_drift_fires_ffi001
  - tests/unit/arch_suite/test_misc.py::TestCppMayThrow::test_noexcept_calling_throwing_function_fires_error
  - tests/gates_suite/test_compliance.py::TestExhaustiveHandlingGate::test_unknown_without_catch_all_fires_exhaust001
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
User mandate 2026-07-22: complement the errors-as-values preference with an EXHAUSTIVE static exception story. Compute a per-function may-raise set: explicit raise sites + resolved callees' sets propagated over the call graph + curated builtin-raiser table (dict[k]->KeyError, int()->ValueError, attr->AttributeError, ...). Unresolvable calls (dynamic dispatch, getattr, plugins) contribute an Unknown marker FAIL-CLOSED, per the T-0339 doctrine -- reuse its per-language resolvers (T-0659..T-0664), do not build a second binding analysis. Ubiquitous asynchronous exceptions (MemoryError, KeyboardInterrupt, SystemExit) live in a separate always-possible tier that exhaustiveness never demands enumerated (only a boundary catch-all may discharge). The normalized model's NormalizedRaise/NormalizedCatch events (T-0609..T-0612) are the substrate. Children: Python may-raise resolver, C++ may-throw + noexcept obligation, exhaustive-handling gate + errors-as-values advisory. Umbrella closes when children close.

<!-- narrative-moved:src/frob/arch/_mayraise_tables.py:86:T-0685 -->
: Curated builtin-raiser table (T-0685/T-0686): bare callee name -> the
: exception type(s) that call is known to be capable of raising, per the
: parent ticket's own examples (`int()`/`float()` casts -> `ValueError`,
: `getattr` reflection -> `AttributeError`, `open`/file IO -> `OSError`,
: `next` on an exhausted iterator -> `StopIteration`). A call whose bare
: name matches a row here is treated as RESOLVED (contributes exactly
: these types, does not also fall through to the unresolved-callee
: `UNKNOWN` path) even though this resolver has no `NormalizedFunction`
: body for it to recurse into -- deliberately narrow (see
: `frob.arch._mayraise`'s module docstring): every callee name NOT in
: this table and NOT a same-module function is fail-closed to `UNKNOWN`,
: not silently assumed safe.
frob:ticket T-0686