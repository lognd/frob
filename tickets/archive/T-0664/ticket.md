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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/**
- src/frob/lang/**
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4718 sweep: move narrative out of over-length comment run in _capability_kotlin.py'
  actor: logan
  at: '2026-09-19'
  old_length: 183
  new_length: 1909
evidence:
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_plain_import_detected
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_detected
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_bare_constructor_detected
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_bare_callable_reference_detected
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typed_callable_reference_detected
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typealias_for_function_type_needs_no_special_resolution
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_chained_val_alias_detected
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_curated_wildcard_import_detected
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_uncurated_wildcard_import_not_detected
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_unaliased_bare_reference_not_detected
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_rejects_non_identifier_member
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_typed_falls_back_to_literal_receiver
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_returns_none_for_unbound_identifier
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_call_expression_wraps_with_parens
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_kt_call_callee_picks_last_non_call_suffix_child
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_plain_import_binds_last_segment
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_as_alias_binds_alias_name
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_curated_wildcard_recorded
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_uncurated_wildcard_not_recorded
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_returns_none_none_without_variable_declaration
- tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_extracts_name_and_value
designated_repro_test: null
acceptance:
- text: Given every Kotlin static-resolvable construct in the taxonomy table, when
    the resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_plain_import_detected
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_detected
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_import_as_bare_constructor_detected
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_bare_callable_reference_detected
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typed_callable_reference_detected
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_typealias_for_function_type_needs_no_special_resolution
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_chained_val_alias_detected
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_curated_wildcard_import_detected
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_uncurated_wildcard_import_not_detected
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinTaxonomyClosureResolution::test_unaliased_bare_reference_not_detected
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_rejects_non_identifier_member
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_callable_reference_typed_falls_back_to_literal_receiver
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_returns_none_for_unbound_identifier
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_resolve_expr_text_call_expression_wraps_with_parens
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_kt_call_callee_picks_last_non_call_suffix_child
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_plain_import_binds_last_segment
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_as_alias_binds_alias_name
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_curated_wildcard_recorded
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_import_table_uncurated_wildcard_not_recorded
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_returns_none_none_without_variable_declaration
  - tests/vet_suite/test_capability_scan_kotlin.py::TestCapabilityScanKotlinAliasTablePredicates::test_property_name_and_value_extracts_name_and_value
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Implement static name-binding resolution for Kotlin per capability-evasion-taxonomy.md's Kotlin table (11 static + 5 opaque entries): import-as, function-reference (::ref), typealias.

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