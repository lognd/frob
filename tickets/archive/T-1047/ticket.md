---
id: T-1047
title: 'vet/opaque: extend RUNTIME_OPAQUE_CONSTRUCTS + OPAQUE_SOURCE_INVISIBLE for
  ~25 taxonomy runtime-opaque rows found unaddressed by T-0666, plus Rust struct-field
  / C++ pointer-to-member alias tracking'
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
- tests/test_vet.py::TestOpaqueIndirectionGate::test_c_weak_symbol_override_excused_source_invisible
- tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_extern_ffi_symbol_excused_source_invisible
- tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_proc_macro_synthesized_call_excused_source_invisible
- tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_runtime_vtable_patch_excused_source_invisible
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_combined_registered_total_matches_112_entry_denominator
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_litmus_path_resolves_to_a_real_test
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_taxonomy_row_has_sufficient_registered_litmus_coverage
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_map_has_no_orphaned_language_category_pairs
designated_repro_test: null
threat: null
component: null
---
T-0666's exhaustive row-by-row litmus-binding pass over
docs/design/capability-evasion-taxonomy.md's 112-entry denominator found
~25 runtime-opaque constructs (across Python, TypeScript/JS, Rust, C, C++,
Kotlin) that have NO entry in `RUNTIME_OPAQUE_CONSTRUCTS` and NO excuse in
`OPAQUE_SOURCE_INVISIBLE` -- meaning `frob.gates._opaque.opaque_gate`
(OPAQUE001) does not fail closed on them at all today, contrary to
T-0339's acceptance criterion [1] ("given any RUNTIME-resolved indirection
... the analyzer FAILS CLOSED"). Also found: a Rust struct-field
points-to gap (struct-update field rebinding never resolves through a
later call), and a C++ pointer-to-member gap (`&Ops::run` / `.*`/`->*`
dereference has no alias tracking at all).

Each gap has a litmus fixture locking the CURRENT honest (non-firing /
non-resolving) behavior in tests/test_vet.py::TestOpaqueIndirectionGate
(the `_not_addressed` suffix tests) and in the per-language
TaxonomyClosureResolution classes (Rust struct-update, C++ member-fn-ptr),
added by T-0666. This ticket tracks closing each one: extend
RUNTIME_OPAQUE_CONSTRUCTS with a detector needle for the constructs that
ARE source-visible (computed member access, globalThis, Reflect, Proxy,
container-dynamic-key patterns, functools.partial, class __getattr__,
sys.modules replacement, integer-cast/void*-backcast function pointers,
non-constant array index, RTTI dispatch, reinterpret_cast, function-value
containers, delegated properties, dynamic classloading), or add a REG011
excuse to OPAQUE_SOURCE_INVISIBLE for the genuinely source-invisible ones
(rust extern-block FFI symbol resolution, matching the existing C
weak-symbol excuse's reasoning). Also add Rust struct-field alias tracking
(mirrors C's `_record_c_field_alias`) and C++ pointer-to-member alias
tracking.

Filed alongside T-0666's Done report (2026-07-27); see that report's
coverage table for the exact fixture -> taxonomy-row mapping this gap
list was built from.