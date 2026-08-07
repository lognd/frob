---
id: T-0659
title: 'vet: exhaustive Python static-binding resolver closure vs capability-evasion-taxonomy.md
  denominator'
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
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_chained_assignment_outer_target_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_chained_assignment_inner_target_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_tuple_unpack_destructuring_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_tuple_unpack_second_element_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_starred_unpack_leading_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_starred_unpack_trailing_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_default_arg_forwarding_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_attribute_target_rebind_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_star_import_reexport_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_conditional_import_fallback_dangerous_first_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_conditional_import_fallback_dangerous_second_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_benign_destructuring_not_detected
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_star_import_untracked_module_not_claimed
- tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_conditional_import_fallback_both_safe_not_detected
designated_repro_test: null
acceptance:
- text: Given every Python static-resolvable construct in the taxonomy's Python table,
    when the resolver runs on a litmus fixture for that construct, then the aliased
    dangerous call is detected
  evidence:
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_chained_assignment_outer_target_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_chained_assignment_inner_target_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_tuple_unpack_destructuring_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_tuple_unpack_second_element_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_starred_unpack_leading_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_starred_unpack_trailing_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_default_arg_forwarding_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_attribute_target_rebind_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_star_import_reexport_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_conditional_import_fallback_dangerous_first_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_conditional_import_fallback_dangerous_second_detected
- text: Given a benign parameter/local binding shadowing a dangerous name, when the
    resolver runs, then it stays silent (no regression)
  evidence:
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_benign_destructuring_not_detected
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_star_import_untracked_module_not_claimed
  - tests/test_vet.py::TestCapabilityScanTaxonomyClosureResolution::test_conditional_import_fallback_both_safe_not_detected
threat: null
component: null
---
T-0328 (import/binding-aware resolution) and T-0337 (local rebinding) are done, but not yet checked against the full capability-evasion-taxonomy.md Python denominator (13 static + 9 opaque entries). Enumerate every remaining Python static construct (chained attribute rebinding, destructuring/unpack aliasing, star-import re-export chains, conditional/try-except import fallback aliasing) and close any gap with a resolver fix + litmus fixture, without regressing shadowing soundness (a benign/param binding must stay silent).