---
id: T-0647
title: 'strata: boundary-flow metrics+traces+logs obligation + trace-id CORRELATION
  propagation'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_observability.py::TestMissingObservability::test_boundary_flow_without_observability_fires
- tests/unit/strata/test_observability.py::TestMissingObservability::test_discharged_and_non_boundary_flows_clean
- tests/unit/strata/test_observability.py::TestMissingObservability::test_waiver_on_one_flow_keeps_sibling_flow_finding
- tests/unit/strata/test_observability.py::TestUnprovenObservability::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_observability.py::TestUnprovenObservability::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_observability.py::TestUnprovenObservability::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/strata/test_observability.py::TestMissingCorrelation::test_second_hop_without_correlation_fires
- tests/unit/strata/test_observability.py::TestMissingCorrelation::test_first_hop_and_discharged_hop_clean
designated_repro_test: null
acceptance:
- text: Given a boundary flow with no metrics/traces/logs declared, when checked,
    then the obligation fires
  evidence:
  - tests/unit/strata/test_observability.py::TestMissingObservability::test_boundary_flow_without_observability_fires
- text: Given a multi-hop flow chain with no trace-id propagation declared, when checked,
    then the obligation fires
  evidence:
  - tests/unit/strata/test_observability.py::TestMissingCorrelation::test_second_hop_without_correlation_fires
threat: null
component: null
---
Every boundary flow must declare metrics+traces+logs instrumentation; a flow chain must propagate a correlation/trace-id across hops (distributed tracing). Proof-against-code required.