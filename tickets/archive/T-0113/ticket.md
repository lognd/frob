---
id: T-0113
title: 'threat C: CWE-sink effect extraction + mitigation chokepoint verification'
state: done
kind: security
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0112
- T-0079
parent: T-0109
tier: ticket
sprint: null
scope:
- docs/strata/**
- src/frob/strata/**
- src/frob/lang/**
- strata-core/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestDischargeChokepointShape::test_reach_claim_does_not_discharge_as_a_chokepoint
- tests/unit/strata/test_threat.py::TestDischargeChokepointShape::test_noflow_claim_with_wrong_dst_does_not_discharge
- tests/unit/strata/test_threat.py::TestDischargeChokepointShape::test_noflow_from_a_specific_foreign_trust_node_discharges
- tests/unit/strata/test_threat.py::TestDischargeChokepointShape::test_noflow_from_a_non_foreign_node_does_not_discharge
- tests/unit/strata/test_threat.py::TestEvaluateThreats::test_binding_and_root_wire_in_threat004_and_threat005
- tests/unit/strata/test_threat.py::TestEvaluateThreats::test_no_binding_or_root_skips_effect_completeness
- tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_undeclared_sink_is_threat004
- tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_declared_capability_silences_threat004
- tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_unclassified_sink_kind_is_threat005
- tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_benign_capability_excuses_threat005
- tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_classified_sink_with_declared_capability_is_clean
- tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_foreign_code_is_not_joined
- tests/unit/strata/test_threat.py::TestCheckEffectCompleteness::test_non_default_catalog_moves_the_sink_taxonomy_with_it
- tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_declassify_boundary_does_not_discharge
- tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_endorse_boundary_with_wrong_predicate_does_not_discharge
- tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_endorse_boundary_with_matching_predicate_discharges
- tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_mixed_paths_matching_on_one_wrong_kind_on_other_does_not_discharge
- tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_assumed_claim_bypasses_the_mitigation_kind_check
designated_repro_test: null
acceptance:
- text: GIVEN localStorage.setItem without a declared capability THEN it errors; GIVEN
    sql not through the parameterized chokepoint THEN CWE-89 refutes
  evidence: []
threat: tampering
component: null
---
extend effect extraction (joins T-0079) to CWE sinks; undeclared-capability-in-code error; mitigation via policy chokepoint forms. threat.md phase C.