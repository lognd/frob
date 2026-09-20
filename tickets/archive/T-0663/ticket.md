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
  old_length: 254
  new_length: 1980
evidence:
- tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_declaration_needs_no_special_resolution
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_namespace_alias_qualified_call_needs_no_special_resolution
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_fn_ptr_var_init_detected_on_cpp_extension
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_alias_declaration_fn_ptr_typedef_detected
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_std_function_init_detected
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_forwarding_detected
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_param_shadowing_call_site_not_detected
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_detected
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_non_literal_rhs_not_detected
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_lambda_capturing_fn_ptr_var_detected
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppAliasTablePredicates::test_structured_binding_alias_skips_non_initializer_list_rhs
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_skips_node_with_no_default_value_field
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_records_resolvable_default
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppAliasTablePredicates::test_scope_bind_step_binds_optional_parameter_declaration
- tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppAliasTablePredicates::test_declaration_alias_dispatches_structured_binding_declarator
designated_repro_test: null
acceptance:
- text: Given every C++ static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/vet_suite/test_capability_scan_c.py::TestCapabilityScanCTaxonomyClosureResolution::test_fn_ptr_var_init_detected
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_declaration_needs_no_special_resolution
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_namespace_alias_qualified_call_needs_no_special_resolution
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_fn_ptr_var_init_detected_on_cpp_extension
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_using_alias_declaration_fn_ptr_typedef_detected
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_std_function_init_detected
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_forwarding_detected
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_default_arg_param_shadowing_call_site_not_detected
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_detected
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_structured_binding_non_literal_rhs_not_detected
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppTaxonomyClosureResolution::test_lambda_capturing_fn_ptr_var_detected
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppAliasTablePredicates::test_structured_binding_alias_skips_non_initializer_list_rhs
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_skips_node_with_no_default_value_field
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppAliasTablePredicates::test_default_param_alias_records_resolvable_default
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppAliasTablePredicates::test_scope_bind_step_binds_optional_parameter_declaration
  - tests/vet_suite/test_capability_scan_cpp.py::TestCapabilityScanCppAliasTablePredicates::test_declaration_alias_dispatches_structured_binding_declarator
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Implement static name-binding resolution for C++ per capability-evasion-taxonomy.md's C++ table (12 static + 5 opaque entries): using-declaration, namespace alias, function-pointer/typedef'd fn-ptr, building on the C resolver's fn-ptr/typedef groundwork.

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