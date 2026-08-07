---
id: T-0643
title: 'strata: FALLBACK/graceful-degradation obligation for CRITICAL dependencies'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0640
- T-0642
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
- tests/unit/strata/test_fallback.py::TestMissingFallback::test_critical_node_without_fallback_fires
- tests/unit/strata/test_fallback.py::TestMissingFallback::test_discharged_and_non_critical_nodes_clean
- tests/unit/strata/test_fallback.py::TestMissingFallback::test_waiver_on_one_node_keeps_sibling_node_finding
- tests/unit/strata/test_fallback.py::TestUnprovenFallback::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_fallback.py::TestUnprovenFallback::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_fallback.py::TestUnprovenFallback::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
acceptance:
- text: Given a CRITICAL dependency with no fallback declared, when checked, then
    the obligation fires
  evidence:
  - tests/unit/strata/test_fallback.py::TestMissingFallback::test_critical_node_without_fallback_fires
  - tests/unit/strata/test_fallback.py::TestMissingFallback::test_discharged_and_non_critical_nodes_clean
  - tests/unit/strata/test_fallback.py::TestMissingFallback::test_waiver_on_one_node_keeps_sibling_node_finding
  - tests/unit/strata/test_fallback.py::TestUnprovenFallback::test_declared_with_no_code_evidence_fires
  - tests/unit/strata/test_fallback.py::TestUnprovenFallback::test_declared_with_real_code_evidence_discharges
  - tests/unit/strata/test_fallback.py::TestUnprovenFallback::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
threat: null
component: null
---
A dependency marked CRITICAL must declare a fallback/graceful-degradation path, and the fallback code path must be shown present (proof-against-code) or explicitly waived. Reuses the circuit-breaker ticket's dependency-criticality classification, hence blocked on that groundwork existing.