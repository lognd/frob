---
id: T-0666
title: 'vet: cross-language exhaustiveness meta-test binding capability-evasion-taxonomy.md
  denominator (112 entries) to per-construct litmus fixtures (T-0339 close condition)'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0659
- T-0660
- T-0661
- T-0662
- T-0663
- T-0664
- T-0665
- T-0390
parent: T-0339
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- docs/design/registry/evasion.yaml
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_doc_heading_recognized
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_litmus_path_resolves_to_a_real_test
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_taxonomy_row_has_sufficient_registered_litmus_coverage
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_map_has_no_orphaned_language_category_pairs
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_combined_registered_total_matches_112_entry_denominator
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_closure_capture_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_with_as_binding_a_callable_bearing_object_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_walrus_operator_bind_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_export_from_reexport_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_export_star_from_reexport_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_export_default_binding_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_class_field_holding_bound_reference_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_named_import_with_alias_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_function_pointer_coercion_from_named_fn_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_type_alias_for_function_pointer_type_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_struct_update_field_rebind_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_macro_rules_expansion_emitting_fixed_call_not_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_namespace_directive_qualified_call_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_define_macro_aliasing_detected_on_cpp_extension
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_member_function_pointer_bound_to_named_member_not_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_argument_dependent_lookup_call_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_destructuring_declaration_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_lambda_closure_capturing_bound_name_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_default_parameter_forwarding_callable_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_operator_fun_invoke_making_object_directly_callable_not_detected
- tests/test_vet.py::TestOpaqueIndirectionGate::test_python_exec_always_fires_regardless_of_argument
- tests/test_vet.py::TestOpaqueIndirectionGate::test_python_setattr_monkeypatch_fires
- tests/test_vet.py::TestOpaqueIndirectionGate::test_python_container_dynamic_key_not_addressed
- tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_eval_always_fires_regardless_of_argument
- tests/test_vet.py::TestOpaqueIndirectionGate::test_typescript_function_constructor_always_fires
- tests/test_vet.py::TestOpaqueIndirectionGate::test_c_integer_cast_to_function_pointer_not_addressed
- tests/test_vet.py::TestOpaqueIndirectionGate::test_c_void_star_backcast_not_addressed
- tests/test_vet.py::TestOpaqueIndirectionGate::test_c_weak_symbol_override_excused_source_invisible
- tests/test_vet.py::TestOpaqueIndirectionGate::test_rust_runtime_vtable_patch_excused_source_invisible
- tests/test_vet.py::TestOpaqueIndirectionGate::test_cpp_virtual_dispatch_bounded_polymorphism_no_finding
- tests/test_vet.py::TestOpaqueIndirectionGate::test_kotlin_kcallable_call_always_fires
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_struct_update_field_rebind_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_destructuring_declaration_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_default_parameter_forwarding_callable_detected
designated_repro_test: null
acceptance:
- text: Given the full evasion taxonomy denominator, when the meta-test runs, then
    every entry maps to >=1 registered litmus fixture
  evidence:
  - tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_taxonomy_row_has_sufficient_registered_litmus_coverage
- text: Given a new taxonomy entry added with no fixture, when the meta-test runs,
    then it fails the build
  evidence:
  - tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_litmus_path_resolves_to_a_real_test
threat: null
component: null
---
Epic close condition. Binds every capability-evasion-taxonomy.md entry (112: 13+9 Python, 17+9 TS/JS, 13+6 Rust, 7+5 C, 12+5 C++, 11+5 Kotlin) to >=1 litmus fixture that exercises it, mirroring the CVE-fingerprint catalog drift-lock. Fails the build if any construct has no fixture. Depends on all per-language resolver tickets and the opaque-indirection obligation landing, plus T-0390 (evasion registry-domain reconciliation) for disposition accuracy.