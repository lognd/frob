"""T-0666: cross-language exhaustiveness litmus-coverage map for
`docs/design/capability-evasion-taxonomy.md` (T-0339's 112-entry
denominator, mirrored in `docs/design/registry/evasion.yaml`'s
`EVA-<LANG>-<S|R><NN>` ids).

Every taxonomy row falls into one of two buckets per language: a
`static`-resolvable name-binding construct the ordinary resolver
(`frob.vet._capability.scan_file_capabilities`) is expected to walk, or a
`runtime`-opaque construct the fail-closed obligation gate
(`frob.gates._opaque.opaque_gate` / `_opaque_indirection_findings`) is
expected to catch (or, for the small SOURCE-INVISIBLE subset, explicitly
excuse via `frob.vet._capability_registry.OPAQUE_SOURCE_INVISIBLE`).

This module is the single, greppable, statically-checkable REGISTRATION
of "row X in the taxonomy doc is proven by test Y" that
`tests/test_vet.py::TestEvasionTaxonomyExhaustiveness` (the T-0666
cross-language exhaustiveness meta-test) validates bidirectionally at test
time: (1) every row the doc's own tables enumerate, per language and
category, has AT LEAST as many registered litmus paths here as the doc
has rows for that (language, category) pair -- a doc row added with no
matching growth here fails the build loudly; (2) every dotted test path
listed here actually exists as a collected test in `tests/test_vet.py` --
a stale/renamed reference fails loudly too, the "dangling ref" direction.

Coverage is NOT claimed to be 1:1 by construct identity for every single
row (a strict per-row id assignment would require the taxonomy doc to
carry its own stable per-row ids, which it does not -- `docs/design/
registry/RECONCILIATION.md` finding (a) notes the registry's own
`EVA-<LANG>-<NNN>` ids were MINTED by that reconciliation pass, not
authored by the source doc). What this map DOES guarantee, checked
mechanically: the litmus COUNT for each (language, category) pair is
never below the doc's own row count for that pair, and every listed
litmus path is real and collectible -- so a new taxonomy row with no
matching new fixture is structurally impossible to land silently.

Several listed litmus paths deliberately assert the CURRENT, honest
NON-detection of a construct (docstring-labelled `_not_detected` /
`_not_addressed` in `tests/test_vet.py`) rather than a passing resolution
-- T-0666's own brief distinguishes "bind every row to >=1 fixture"
(this module's job) from "every construct genuinely resolves"
(T-339's epic acceptance, a separate, stricter bar not fully met by every
row here; see T-1047 for the tracked follow-up closing each
documented gap).
"""

from __future__ import annotations

#: Doc `## <heading>` text (as it appears verbatim in
#: `docs/design/capability-evasion-taxonomy.md`) -> this module's
#: normalized language key. TypeScript and JavaScript share one table in
#: the doc (one heading, one row set) and therefore one key here.
_DOC_HEADING_TO_LANGUAGE_KEY: dict[str, str] = {
    "Python": "python",
    "TypeScript / JavaScript": "typescript",
    "Rust": "rust",
    "C": "c",
    "C++": "cpp",
    "Kotlin": "kotlin",
}

#: (language_key, "static" | "runtime") -> dotted `Class.method` test refs
#: in `tests/test_vet.py`, one per taxonomy row this pass could bind (some
#: rows share a fixture where the underlying code path is provably
#: identical -- documented inline in each test's own docstring, e.g. the
#: C++ `using`-alias-declaration row reducing to the same `init_declarator`
#: path C's typedef row already locks).
_EVASION_LITMUS_MAP: dict[tuple[str, str], tuple[str, ...]] = {
    ("python", "static"): (
        "TestCapabilityScan.test_python_exec_and_net_detected",
        "TestCapabilityScanBindingResolution.test_import_as_alias_detected",
        "TestCapabilityScanBindingResolution.test_from_import_detected",
        "TestCapabilityScanBindingResolution.test_from_import_as_detected_with_correct_kind",
        "TestCapabilityScanTaxonomyClosureResolution.test_star_import_reexport_detected",
        "TestCapabilityScanLocalRebindResolution.test_single_rebind_detected",
        "TestCapabilityScanTaxonomyClosureResolution.test_chained_assignment_outer_target_detected",
        "TestCapabilityScanTaxonomyClosureResolution.test_tuple_unpack_destructuring_detected",
        "TestCapabilityScanTaxonomyClosureResolution.test_starred_unpack_leading_detected",
        "TestCapabilityScanTaxonomyClosureResolution.test_attribute_target_rebind_detected",
        "TestCapabilityScanTaxonomyClosureResolution.test_default_arg_forwarding_detected",
        "TestCapabilityScanTaxonomyClosureResolution.test_closure_capture_detected",
        "TestCapabilityScanTaxonomyClosureResolution.test_with_as_binding_a_callable_bearing_object_detected",
        "TestCapabilityScanTaxonomyClosureResolution.test_walrus_operator_bind_detected",
    ),
    ("python", "runtime"): (
        "TestOpaqueIndirectionGate.test_python_getattr_non_literal_name_fires",
        "TestOpaqueIndirectionGate.test_python_dunder_import_computed_name_fires",
        "TestOpaqueIndirectionGate.test_python_import_module_non_literal_fires",
        "TestOpaqueIndirectionGate.test_python_eval_always_fires_regardless_of_argument",
        "TestOpaqueIndirectionGate.test_python_exec_always_fires_regardless_of_argument",
        "TestOpaqueIndirectionGate.test_python_container_dynamic_key_not_addressed",
        "TestOpaqueIndirectionGate.test_python_setattr_monkeypatch_fires",
        "TestOpaqueIndirectionGate.test_python_functools_partial_dynamic_target_fires",
        "TestOpaqueIndirectionGate.test_python_dunder_getattr_class_interception_fires",
        "TestOpaqueIndirectionGate.test_python_sys_modules_replacement_fires",
    ),
    ("typescript", "static"): (
        "TestCapabilityScanTsBindingResolution.test_direct_unaliased_call_still_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_named_import_with_alias_detected",
        "TestCapabilityScanTsBindingResolution.test_namespace_import_detected",
        "TestCapabilityScanTsBindingResolution.test_default_import_alias_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_export_from_reexport_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_export_star_from_reexport_detected",
        "TestCapabilityScanTsBindingResolution.test_require_bare_detected",
        "TestCapabilityScanTsBindingResolution.test_ts_import_require_clause_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_simple_assignment_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_chained_assignment_outer_target_detected",
        "TestCapabilityScanTsBindingResolution.test_require_destructure_rename_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_array_destructure_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_member_rebind_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_default_param_forwarding_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_closure_capture_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_class_field_holding_bound_reference_detected",
        "TestCapabilityScanTsTaxonomyClosureResolution.test_export_default_binding_detected",
    ),
    ("typescript", "runtime"): (
        "TestOpaqueIndirectionGate.test_typescript_computed_member_non_constant_key_not_addressed",
        "TestOpaqueIndirectionGate.test_typescript_global_this_bracket_fires",
        "TestOpaqueIndirectionGate.test_typescript_reflect_apply_dynamic_target_fires",
        "TestOpaqueIndirectionGate.test_typescript_eval_always_fires_regardless_of_argument",
        "TestOpaqueIndirectionGate.test_typescript_function_constructor_always_fires",
        "TestOpaqueIndirectionGate.test_typescript_dynamic_import_non_literal_specifier_fires",
        "TestOpaqueIndirectionGate.test_typescript_proxy_interception_fires",
        "TestOpaqueIndirectionGate.test_typescript_container_dynamic_key_not_addressed",
        "TestOpaqueIndirectionGate.test_typescript_monkeypatch_module_namespace_fires",
    ),
    ("rust", "static"): (
        "TestCapabilityScanRustBindingResolution.test_use_as_alias_detected",
        "TestCapabilityScanRustBindingResolution.test_bare_use_import_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_grouped_use_alias_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_glob_use_let_alias_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_pub_use_reexport_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_let_binding_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_chained_shadowed_let_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_tuple_destructure_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_struct_update_field_rebind_not_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_type_alias_for_function_pointer_type_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_function_pointer_coercion_from_named_fn_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_closure_capture_detected",
        "TestCapabilityScanRustTaxonomyClosureResolution.test_macro_rules_expansion_emitting_fixed_call_not_detected",
    ),
    ("rust", "runtime"): (
        "TestOpaqueIndirectionGate.test_rust_trait_object_dynamic_dispatch_not_addressed",
        "TestOpaqueIndirectionGate.test_rust_extern_ffi_symbol_excused_source_invisible",
        "TestOpaqueIndirectionGate.test_rust_libloading_get_fires_only_when_file_uses_libloading",
        "TestOpaqueIndirectionGate.test_rust_function_pointer_in_container_fires",
        "TestOpaqueIndirectionGate.test_rust_boxed_dyn_fn_runtime_selected_fires",
        "TestOpaqueIndirectionGate.test_rust_proc_macro_synthesized_call_excused_source_invisible",
    ),
    ("c", "static"): (
        "TestCapabilityScan.test_c_source_exec_detected",
        "TestCapabilityScanCTaxonomyClosureResolution.test_fn_ptr_var_init_detected",
        "TestCapabilityScanCTaxonomyClosureResolution.test_assignment_address_of_detected",
        "TestCapabilityScanCTaxonomyClosureResolution.test_typedef_fn_ptr_detected",
        "TestCapabilityScanCBindingResolution.test_macro_alias_detected",
        "TestCapabilityScanCTaxonomyClosureResolution.test_struct_field_static_init_detected",
        "TestCapabilityScanCTaxonomyClosureResolution.test_array_fn_ptr_constant_index_detected",
    ),
    ("c", "runtime"): (
        "TestOpaqueIndirectionGate.test_c_array_nonconstant_index_not_addressed",
        "TestOpaqueIndirectionGate.test_c_dlsym_non_literal_symbol_fires",
        "TestOpaqueIndirectionGate.test_c_integer_cast_to_function_pointer_not_addressed",
        "TestOpaqueIndirectionGate.test_c_void_star_backcast_not_addressed",
        "TestOpaqueIndirectionGate.test_c_weak_symbol_override_excused_source_invisible",
    ),
    ("cpp", "static"): (
        "TestCapabilityScanCppTaxonomyClosureResolution.test_using_declaration_needs_no_special_resolution",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_using_namespace_directive_qualified_call_detected",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_namespace_alias_qualified_call_needs_no_special_resolution",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_define_macro_aliasing_detected_on_cpp_extension",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_fn_ptr_var_init_detected_on_cpp_extension",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_using_alias_declaration_fn_ptr_typedef_detected",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_std_function_init_detected",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_member_function_pointer_bound_to_named_member_not_detected",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_lambda_capturing_fn_ptr_var_detected",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_default_arg_forwarding_detected",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_structured_binding_detected",
        "TestCapabilityScanCppTaxonomyClosureResolution.test_argument_dependent_lookup_call_detected",
    ),
    ("cpp", "runtime"): (
        "TestOpaqueIndirectionGate.test_cpp_array_runtime_index_not_addressed",
        "TestOpaqueIndirectionGate.test_cpp_virtual_dispatch_bounded_polymorphism_no_finding",
        "TestOpaqueIndirectionGate.test_c_dlsym_non_literal_symbol_fires",
        "TestOpaqueIndirectionGate.test_cpp_reinterpret_cast_to_function_pointer_fires",
        "TestOpaqueIndirectionGate.test_cpp_rtti_driven_dispatch_fires",
    ),
    ("kotlin", "static"): (
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_plain_import_detected",
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_import_as_detected",
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_curated_wildcard_import_detected",
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_chained_val_alias_detected",
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_destructuring_declaration_not_detected",
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_bare_callable_reference_detected",
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_typealias_for_function_type_needs_no_special_resolution",
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_lambda_closure_capturing_bound_name_detected",
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_default_parameter_forwarding_callable_not_detected",
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_extension_function_reference_bound_via_import_detected",
        "TestCapabilityScanKotlinTaxonomyClosureResolution.test_operator_fun_invoke_making_object_directly_callable_not_detected",
    ),
    ("kotlin", "runtime"): (
        "TestOpaqueIndirectionGate.test_kotlin_class_forname_always_fires",
        "TestOpaqueIndirectionGate.test_kotlin_kcallable_call_always_fires",
        "TestOpaqueIndirectionGate.test_kotlin_function_value_in_container_fires",
        "TestOpaqueIndirectionGate.test_kotlin_delegated_property_by_fires",
        "TestOpaqueIndirectionGate.test_kotlin_dynamic_classloading_fires",
    ),
}
