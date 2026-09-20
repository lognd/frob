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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/vet.md
  reason: T-0662 refreshed scan_file_capabilities' vet.md doc entry to cover the resolver's
    per-language binding-aware fallback added by this ticket, per AFFECT001
  actor: logan
  at: '2026-07-27'
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_kotlin.py'
  actor: logan
  at: '2026-09-19'
  old_length: 241
  new_length: 1967
evidence:
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_typedef_fn_ptr_detected
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_address_of_detected
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_bare_name_detected
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_struct_field_static_init_detected
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_constant_index_detected
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_nonconstant_index_not_detected
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_chained_var_alias_detected
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_param_shadowing_var_alias_not_detected
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_unaliased_local_shadow_not_detected
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_unwraps_address_of
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_address_of
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_non_pointer
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_via_macro_table
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_record_field_alias_skips_non_field_designator
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_rejects_non_constant_field_type
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_subscript_non_number_index
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_none_node
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_direct_identifier
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_walks_declarator_field_to_identifier
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_parenthesized_declarator_fallback
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_abstract_declarator
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_bare_identifier
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_init_declarator
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_uninitialized_fn_ptr
designated_repro_test: null
acceptance:
- text: Given every C static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_typedef_fn_ptr_detected
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_address_of_detected
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_assignment_bare_name_detected
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_struct_field_static_init_detected
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_constant_index_detected
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_array_fn_ptr_nonconstant_index_not_detected
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_chained_var_alias_detected
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_param_shadowing_var_alias_not_detected
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_unaliased_local_shadow_not_detected
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_unwraps_address_of
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_address_of
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_rejects_non_identifier_non_pointer
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_resolve_alias_source_via_macro_table
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_record_field_alias_skips_non_field_designator
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_rejects_non_constant_field_type
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_c_call_target_resolved_subscript_non_number_index
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_none_node
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_direct_identifier
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_walks_declarator_field_to_identifier
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_parenthesized_declarator_fallback
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_declared_name_returns_none_for_abstract_declarator
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_bare_identifier
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_init_declarator
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCAliasTablePredicates::test_collect_declaration_names_uninitialized_fn_ptr
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Implement static name-binding resolution for C per capability-evasion-taxonomy.md's C table (7 static + 5 opaque entries): #define macro aliasing, function-pointer variable initialized from a named function, typedef'd function-pointer types.

T-4718 sweep (condensed from src/frob/vet/_capability_kotlin.py:19-42,
trimmed for DOCARCH002's 12-line cap): the trimmed block's full original
text, kept verbatim below.

# --------------------------------------------------------------- kotlin (T-0664)
#
# Kotlin static-binding resolution (docs/design/capability-evasion-
# taxonomy.md's Kotlin table, T-0664 -- the fourth per-language resolver
# after T-0328/T-0377/T-0378/T-0379/T-0662/T-0663's python/TS/rust/C/C++
# ones). `frob.lang.raw_tree`'s `"kotlin"` label reaches `frob.lang._walk_
# kotlin`'s grammar via T-0723's central-dispatch wiring.
#
# SCOPE, disclosed up front rather than silently narrowed: this resolver
# uses a FLAT, FILE-WIDE alias table (no per-scope/position shadow
# discipline the way `_c_shadowing_scope`/`_rust_shadowing_scope` give the
# C/rust resolvers) -- a local variable that happens to share a name with
# an imported/aliased binding is NOT distinguished from the import here.
# This is a REDUCED-FIDELITY model versus the other four resolvers (a
# genuine over-approximation risk, not a silent gap: a shadowing local
# could theoretically cause a spurious "detected" on a name that is
# locally rebound to something harmless), accepted for this pass given
# kotlin's own grammar has no separate compilation-unit-vs-function-body
# scope split as clean as C's `_C_SCOPE_TYPES`/rust's `_RUST_SCOPE_TYPES`
# to hang position-aware bookkeeping off of without materially more
# machinery than this ticket's own time budget allows. A future pass
# tightening this to per-function scoping (mirroring `_c_scope_bound_
# names`'s shape against kotlin's `function_declaration`/`class_body`
# nodes) is a natural follow-up, not attempted here.