---
id: T-0660
title: 'vet: exhaustive TypeScript/JS static-binding resolver (import/import-as/from-import/star-import/re-export/destructuring)'
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
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_simple_assignment_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_chained_assignment_outer_target_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_chained_assignment_inner_target_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_array_destructure_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_default_param_forwarding_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_member_rebind_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_closure_capture_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_reassigned_alias_call_via_chained_target_still_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_default_param_benign_not_detected
- tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_member_rebind_benign_not_detected
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
- text: Given every TS/JS static-resolvable construct in the taxonomy table, when
    the resolver runs on its litmus fixture, then the aliased dangerous call is detected
  evidence:
  - tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_simple_assignment_detected
  - tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_chained_assignment_outer_target_detected
  - tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_chained_assignment_inner_target_detected
  - tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_array_destructure_detected
  - tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_default_param_forwarding_detected
  - tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_member_rebind_detected
  - tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_closure_capture_detected
  - tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_reassigned_alias_call_via_chained_target_still_detected
  - tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_default_param_benign_not_detected
  - tests/test_vet.py::TestCapabilityScanTsTaxonomyClosureResolution::test_member_rebind_benign_not_detected
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
Implement per-scope, transitive, cycle-guarded static name-binding resolution for TS/JS per capability-evasion-taxonomy.md's TS/JS table (17 static + 9 opaque entries): import/import-as, named/default/namespace import, re-export (export ... from), destructuring assignment, CommonJS require aliasing where statically resolvable.