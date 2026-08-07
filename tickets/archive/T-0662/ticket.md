---
id: T-0662
title: 'vet: exhaustive C static-binding resolver (#define, fn-ptr init from named
  fn, typedef''d fn-ptr)'
state: done
kind: security
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0339
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: T-0662 refreshed scan_file_capabilities' vet.md doc entry to cover the resolver's
    per-language binding-aware fallback added by this ticket, per AFFECT001
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_typedef_fn_ptr_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_address_of_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_bare_name_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_struct_field_static_init_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_constant_index_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_nonconstant_index_not_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_chained_var_alias_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_param_shadowing_var_alias_not_detected
- tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_unaliased_local_shadow_not_detected
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_unwraps_address_of
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_address_of
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_non_pointer
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_via_macro_table
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_record_field_alias_skips_non_field_designator
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_rejects_non_constant_field_type
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_subscript_non_number_index
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_none_node
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_direct_identifier
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_walks_declarator_field_to_identifier
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_parenthesized_declarator_fallback
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_abstract_declarator
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_bare_identifier
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_init_declarator
- tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_uninitialized_fn_ptr
designated_repro_test: null
acceptance:
- text: Given every C static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_typedef_fn_ptr_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_address_of_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_bare_name_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_struct_field_static_init_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_constant_index_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_nonconstant_index_not_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_chained_var_alias_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_param_shadowing_var_alias_not_detected
  - tests/test_vet.py::TestCapabilityScanCTaxonomyClosureResolution::test_unaliased_local_shadow_not_detected
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_unwraps_address_of
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_address_of
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_non_pointer
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_via_macro_table
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_record_field_alias_skips_non_field_designator
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_rejects_non_constant_field_type
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_subscript_non_number_index
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_none_node
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_direct_identifier
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_walks_declarator_field_to_identifier
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_parenthesized_declarator_fallback
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_abstract_declarator
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_bare_identifier
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_init_declarator
  - tests/test_vet.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_uninitialized_fn_ptr
threat: null
component: null
---
Implement static name-binding resolution for C per capability-evasion-taxonomy.md's C table (7 static + 5 opaque entries): #define macro aliasing, function-pointer variable initialized from a named function, typedef'd function-pointer types.