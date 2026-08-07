---
id: T-0661
title: 'vet: exhaustive Rust static-binding resolver (use/use-as/pub use/glob use)'
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
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_grouped_use_alias_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_nested_grouped_use_alias_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_pub_use_reexport_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_glob_use_let_alias_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_let_binding_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_chained_shadowed_let_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_tuple_destructure_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_closure_capture_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_glob_use_untracked_module_not_claimed
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_closure_param_shadowing_let_alias_not_detected
- tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_let_binding_benign_not_detected
- tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_used_only_for_identifier_object
- tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_skipped_without_alias_table
- tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_attr_rebind_lookup_climbs_past_non_matching_scope
- tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_resolve_expr_peels_through_chained_assignment
- tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_recorded_for_identifier_pattern
- tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_skips_missing_default_value
- tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_tolerates_length_mismatch
- tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_binds_only_identifier_elements
designated_repro_test: null
acceptance:
- text: Given every Rust static-resolvable construct in the taxonomy table, when the
    resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_grouped_use_alias_detected
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_nested_grouped_use_alias_detected
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_pub_use_reexport_detected
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_glob_use_let_alias_detected
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_let_binding_detected
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_chained_shadowed_let_detected
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_tuple_destructure_detected
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_closure_capture_detected
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_glob_use_untracked_module_not_claimed
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_closure_param_shadowing_let_alias_not_detected
  - tests/test_vet.py::TestCapabilityScanRustTaxonomyClosureResolution::test_let_binding_benign_not_detected
  - tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_used_only_for_identifier_object
  - tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_member_rebind_lookup_skipped_without_alias_table
  - tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_attr_rebind_lookup_climbs_past_non_matching_scope
  - tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_resolve_expr_peels_through_chained_assignment
  - tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_recorded_for_identifier_pattern
  - tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_default_param_alias_skips_missing_default_value
  - tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_tolerates_length_mismatch
  - tests/test_vet.py::TestCapabilityScanTsAliasTablePredicates::test_destructure_alias_binds_only_identifier_elements
threat: null
component: null
---
Implement per-scope, transitive, cycle-guarded static name-binding resolution for Rust per capability-evasion-taxonomy.md's Rust table (13 static + 6 opaque entries): use, use ... as, pub use re-export, glob use, module-path aliasing.