---
id: T-0663
title: 'vet: exhaustive C++ static-binding resolver (using-decl, namespace alias,
  fn-ptr/typedef, on top of C fragment)'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0662
parent: T-0339
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_declaration_needs_no_special_resolution
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_namespace_alias_qualified_call_needs_no_special_resolution
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_fn_ptr_var_init_detected_on_cpp_extension
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_alias_declaration_fn_ptr_typedef_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_std_function_init_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_forwarding_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_param_shadowing_call_site_not_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_non_literal_rhs_not_detected
- tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_lambda_capturing_fn_ptr_var_detected
- tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_structured_binding_alias_skips_non_initializer_list_rhs
- tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_skips_node_with_no_default_value_field
- tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_records_resolvable_default
- tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_scope_bind_step_binds_optional_parameter_declaration
- tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_declaration_alias_dispatches_structured_binding_declarator
designated_repro_test: null
acceptance:
- text: Given every C++ static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_declaration_needs_no_special_resolution
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_namespace_alias_qualified_call_needs_no_special_resolution
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_fn_ptr_var_init_detected_on_cpp_extension
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_alias_declaration_fn_ptr_typedef_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_std_function_init_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_forwarding_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_param_shadowing_call_site_not_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_non_literal_rhs_not_detected
  - tests/test_vet.py::TestCapabilityScanCppTaxonomyClosureResolution::test_lambda_capturing_fn_ptr_var_detected
  - tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_structured_binding_alias_skips_non_initializer_list_rhs
  - tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_skips_node_with_no_default_value_field
  - tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_records_resolvable_default
  - tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_scope_bind_step_binds_optional_parameter_declaration
  - tests/test_vet.py::TestCapabilityScanCppAliasTablePredicates::test_declaration_alias_dispatches_structured_binding_declarator
threat: null
component: null
---
Implement static name-binding resolution for C++ per capability-evasion-taxonomy.md's C++ table (12 static + 5 opaque entries): using-declaration, namespace alias, function-pointer/typedef'd fn-ptr, building on the C resolver's fn-ptr/typedef groundwork.