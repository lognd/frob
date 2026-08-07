---
id: T-0664
title: 'vet: exhaustive Kotlin static-binding resolver (import-as, ::ref, typealias)'
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_plain_import_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_bare_constructor_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_bare_callable_reference_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typed_callable_reference_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typealias_for_function_type_needs_no_special_resolution
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_chained_val_alias_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_curated_wildcard_import_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_uncurated_wildcard_import_not_detected
- tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_unaliased_bare_reference_not_detected
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_rejects_non_identifier_member
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_typed_falls_back_to_literal_receiver
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_returns_none_for_unbound_identifier
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_call_expression_wraps_with_parens
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_kt_call_callee_picks_last_non_call_suffix_child
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_plain_import_binds_last_segment
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_as_alias_binds_alias_name
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_curated_wildcard_recorded
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_uncurated_wildcard_not_recorded
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_returns_none_none_without_variable_declaration
- tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_extracts_name_and_value
designated_repro_test: null
acceptance:
- text: Given every Kotlin static-resolvable construct in the taxonomy table, when
    the resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_plain_import_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_bare_constructor_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_bare_callable_reference_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typed_callable_reference_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typealias_for_function_type_needs_no_special_resolution
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_chained_val_alias_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_curated_wildcard_import_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_uncurated_wildcard_import_not_detected
  - tests/test_vet.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_unaliased_bare_reference_not_detected
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_rejects_non_identifier_member
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_typed_falls_back_to_literal_receiver
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_returns_none_for_unbound_identifier
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_call_expression_wraps_with_parens
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_kt_call_callee_picks_last_non_call_suffix_child
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_plain_import_binds_last_segment
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_as_alias_binds_alias_name
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_curated_wildcard_recorded
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_uncurated_wildcard_not_recorded
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_returns_none_none_without_variable_declaration
  - tests/test_vet.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_extracts_name_and_value
threat: null
component: null
---
Implement static name-binding resolution for Kotlin per capability-evasion-taxonomy.md's Kotlin table (11 static + 5 opaque entries): import-as, function-reference (::ref), typealias.