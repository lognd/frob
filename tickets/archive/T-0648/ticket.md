---
id: T-0648
title: 'strata: golden-signal SLO + error-budget obligation per service'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0647
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
- tests/unit/strata/test_slo.py::TestMissingSlo::test_service_node_without_slo_fires
- tests/unit/strata/test_slo.py::TestMissingSlo::test_only_slo_or_only_error_budget_still_fires
- tests/unit/strata/test_slo.py::TestMissingSlo::test_discharged_and_non_service_nodes_clean
- tests/unit/strata/test_slo.py::TestMissingSlo::test_waiver_discharges_finding
- tests/unit/strata/test_slo.py::TestUnprovenSlo::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_slo.py::TestUnprovenSlo::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_slo.py::TestUnprovenSlo::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
acceptance:
- text: Given a service node with no golden-signal SLOs + error budget declared, when
    checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_slo.py::TestMissingSlo::test_service_node_without_slo_fires
  - tests/unit/strata/test_slo.py::TestMissingSlo::test_only_slo_or_only_error_budget_still_fires
  - tests/unit/strata/test_slo.py::TestMissingSlo::test_discharged_and_non_service_nodes_clean
  - tests/unit/strata/test_slo.py::TestMissingSlo::test_waiver_discharges_finding
  - tests/unit/strata/test_slo.py::TestUnprovenSlo::test_declared_with_no_code_evidence_fires
  - tests/unit/strata/test_slo.py::TestUnprovenSlo::test_declared_with_real_code_evidence_discharges
  - tests/unit/strata/test_slo.py::TestUnprovenSlo::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
threat: null
component: null
---
Every service node must declare golden-signal SLOs (latency/traffic/errors/saturation) and an error budget. Depends on the metrics-instrumentation obligation existing first, since an SLO without the underlying signal is unverifiable.