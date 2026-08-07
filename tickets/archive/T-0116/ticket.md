---
id: T-0116
title: 'threat G: std.compliance -- COPPA/GDPR/HIPAA + privacy-policy-as-claims'
state: done
kind: security
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0111
parent: T-0109
tier: ticket
sprint: null
scope:
- docs/strata/**
- src/frob/strata/**
- strata-core/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_compliance.py::TestRegulationCatalogCompleteness::test_full_catalog_satisfies_all_regulations_view
- tests/unit/strata/test_compliance.py::TestRegulationCatalogCompleteness::test_missing_entry_is_a_violation
- tests/unit/strata/test_compliance.py::TestRegulationCatalogCompleteness::test_out_of_scope_entry_excuses_a_missing_catalog_entry
- tests/unit/strata/test_compliance.py::TestRegulationCatalogCompleteness::test_unknown_view_fails_closed
- tests/unit/strata/test_compliance.py::TestRegulationCatalogCompleteness::test_views_table_is_data_driven
- tests/unit/strata/test_compliance.py::TestCoppa::test_ungated_child_collection_flow_refutes_coppa
- tests/unit/strata/test_compliance.py::TestCoppa::test_age_gate_boundary_discharges_coppa
- tests/unit/strata/test_compliance.py::TestCoppa::test_assumed_claim_with_owner_and_review_overrides
- tests/unit/strata/test_compliance.py::TestCoppa::test_assumed_claim_with_no_owner_is_a_violation
- tests/unit/strata/test_compliance.py::TestGdprErasure::test_eu_resident_store_with_no_deletion_path_refutes_erasure
- tests/unit/strata/test_compliance.py::TestGdprErasure::test_revocation_edge_discharges_erasure
- tests/unit/strata/test_compliance.py::TestGdprRetention::test_store_past_declared_retention_refutes
- tests/unit/strata/test_compliance.py::TestGdprRetention::test_store_within_retention_bound_passes
- tests/unit/strata/test_compliance.py::TestGdprLawfulBasis::test_no_declared_basis_refutes
- tests/unit/strata/test_compliance.py::TestGdprLawfulBasis::test_declared_basis_discharges
- tests/unit/strata/test_compliance.py::TestHipaaBaa::test_health_flow_to_uncovered_party_refutes
- tests/unit/strata/test_compliance.py::TestHipaaBaa::test_covered_party_attestation_discharges
- tests/unit/strata/test_compliance.py::TestMinimization::test_collected_but_never_read_is_a_violation
- tests/unit/strata/test_compliance.py::TestMinimization::test_downstream_read_discharges
- tests/unit/strata/test_compliance.py::TestPrivacyPolicy::test_field_the_policy_omits_refutes
- tests/unit/strata/test_compliance.py::TestPrivacyPolicy::test_declared_field_passes
- tests/unit/strata/test_compliance.py::TestEvaluateCompliance::test_conjunction_of_catalog_discharge_and_policy
- tests/unit/strata/test_compliance.py::TestEvaluateCompliance::test_unknown_view_fails_closed
- tests/unit/strata/test_compliance.py::TestCoppa::test_declassify_only_boundary_does_not_discharge_coppa
designated_repro_test: null
acceptance:
- text: GIVEN a child-tagged collection flow with no consent boundary THEN COPPA refutes;
    GIVEN eu-resident Pii with no deletion path THEN erasure refutes; GIVEN a flow
    collecting a field the privacy policy omits THEN it refutes
  evidence: []
threat: info-disclosure
component: null
---
compliance family: data-subject tags (child/health/biometric/jurisdiction) on labels; regulation entries scoped by jurisdiction; obligations per the threat.md compliance table (COPPA age-gate, GDPR erasure=revocation-edge, retention=age-bound, lawful basis, HIPAA BAA, minimization); privacy-policy-as-assert reverse audit bound by DOC002; per-regulation exhaustiveness with legally-owned expiring assumes. Reuses closure/age-collapse/revocation-edge. threat.md compliance section.