---
id: T-1024
title: 'REF/COV/DEAD/PLACE small-bucket sweep: REF001 36 orphan invariant docs, COV007
  38 private-symbol doc anchors, DEAD001 13, REF002 6, COV006 3, PLACE001 2'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- invariants/
- docs/
- src/frob/
- tests/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_doc_heading_recognized
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_litmus_path_resolves_to_a_real_test
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_taxonomy_row_has_sufficient_registered_litmus_coverage
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_map_has_no_orphaned_language_category_pairs
- tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_combined_registered_total_matches_112_entry_denominator
- tests/test_vet.py::TestOpaqueIndirectionGate::test_python_getattr_non_literal_name_fires
- tests/unit/test_design_invariants.py::TestInv007::test_forbidden_import_fires
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
- tests/test_registry_exhaustiveness.py::TestDisposition::test_undispositioned_entry_fails
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check THEN REF001/REF002/COV006/COV007/DEAD001/PLACE001
    warnings are zero
  evidence:
  - tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_doc_heading_recognized
  - tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_litmus_path_resolves_to_a_real_test
  - tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_every_taxonomy_row_has_sufficient_registered_litmus_coverage
  - tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_map_has_no_orphaned_language_category_pairs
  - tests/test_vet.py::TestEvasionTaxonomyExhaustiveness::test_combined_registered_total_matches_112_entry_denominator
  - tests/test_vet.py::TestOpaqueIndirectionGate::test_python_getattr_non_literal_name_fires
  - tests/unit/test_design_invariants.py::TestInv007::test_forbidden_import_fires
  - tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
  - tests/test_registry_exhaustiveness.py::TestDisposition::test_undispositioned_entry_fails
threat: null
component: null
---
Sweep the small warning buckets: REF001 orphan invariants/*.md need real inbound references (frob:used-by or doc links from the module docs that rely on them); REF002 single-anchor docs need a second consumer; COV007 move frob:doc anchors from private symbols to the public surface they document; COV006 fix the flagged frob:tests edges; DEAD001 delete or bind the 13 uncalled private test helpers; PLACE001 move the 2 misplaced directives onto their intended symbols.