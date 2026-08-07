---
id: T-1051
title: 'vet/opaque: close remaining 13 taxonomy runtime-opaque rows (generalized subscript/cast
  detector + rust/cpp/kotlin alias tracking)'
state: done
kind: security
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/gates/_opaque.py
- docs/design/registry/evasion.yaml
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestOpaqueIndirectionGate::test_python_container_dynamic_key_not_addressed
- tests/test_vet.py::TestOpaqueIndirectionGate::test_python_container_literal_key_call_not_addressed_by_structural_gate
- tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_computed_member_non_constant_key_not_addressed
- tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_container_dynamic_key_not_addressed
- tests/test_vet.py::TestOpaqueIndirectionGate::test_c_array_nonconstant_index_not_addressed
- tests/test_vet.py::TestOpaqueIndirectionGate::test_c_integer_cast_to_function_pointer_not_addressed
- tests/test_vet.py::TestOpaqueIndirectionGate::test_c_void_star_backcast_not_addressed
- tests/test_vet.py::TestOpaqueIndirectionGate::test_cpp_array_runtime_index_not_addressed
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_taxonomy_row_has_sufficient_registered_litmus_coverage
- tests/test_vet.py::TestOpaqueIndirectionGate::test_opaque_structural_construct_is_frozen
designated_repro_test: null
threat: null
component: null
---
T-1047 closed 17 of the ~25 taxonomy runtime-opaque gaps T-0666's litmus
pass found unaddressed (RUNTIME_OPAQUE_CONSTRUCTS gained 15 needle
entries across python/typescript/c-cpp/rust/kotlin; OPAQUE_SOURCE_INVISIBLE
gained 2 rust category-3 excuses). 13 rows remain, each already locked by
an honest non-firing/non-resolving litmus fixture in
tests/test_vet.py::TestOpaqueIndirectionGate (untouched by T-1047):

Needle-architecture-blocked (need a generalized subscript-or-cast detector
shape, not another single-literal needle -- the current
RUNTIME_OPAQUE_CONSTRUCTS needle+single-literal-arg architecture cannot
express these without an unacceptable false-positive rate):
- python: container-dynamic-key call (dict[computed_key](...))
- python: computed-member access with non-constant key
- typescript: container-dynamic-key call
- typescript: computed-member access with non-constant key
- c/c++: array-index function-pointer dispatch (fn_table[i]())
- c/c++: integer-cast-to-function-pointer
- c/c++: void*-backcast-to-function-pointer

Structural resolver-level points-to gaps (need real alias tracking added
to the ordinary per-language resolvers, not a registry-entry addition):
- rust: struct-update field rebinding (struct-update syntax never
  resolves a rebound field through a later call, mirrors C's
  _record_c_field_alias which this ticket should generalize from)
- rust: macro_rules! expansion (macro-synthesized call sites invisible to
  a per-source-file scan)
- c++: pointer-to-member (&Ops::run / .* / ->* dereference has no alias
  tracking at all)
- kotlin: destructuring declarations
- kotlin: default-parameter-bound callables
- kotlin: operator-invoke (operator fun invoke)

Because these 13 rows are unaddressed, T-0339's acceptance criterion [1]
("given any RUNTIME-resolved indirection ... the analyzer FAILS CLOSED")
does not fully hold. T-0339 remains open until this closes (or until each
remaining row gets a reasoned OPAQUE_SOURCE_INVISIBLE excuse instead, if
investigation shows any of them are genuinely source-invisible per T-0665
doctrine rather than needing a detector/resolver).