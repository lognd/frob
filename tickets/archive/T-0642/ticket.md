---
id: T-0642
title: 'strata: CIRCUIT BREAKER / bulkhead obligation per external dependency'
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
- tests/unit/strata/test_circuit_breaker.py::TestPredicates::test_is_external_dependency
- tests/unit/strata/test_circuit_breaker.py::TestPredicates::test_is_critical_dependency
- tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::test_external_node_without_circuit_breaker_fires
- tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::test_discharged_and_non_external_nodes_clean
- tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::test_waiver_on_one_node_keeps_sibling_node_finding
- tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
acceptance:
- text: Given an external-dependency node with no circuit-breaker/bulkhead declared,
    when checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_circuit_breaker.py::TestPredicates::test_is_external_dependency
  - tests/unit/strata/test_circuit_breaker.py::TestPredicates::test_is_critical_dependency
  - tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::test_external_node_without_circuit_breaker_fires
  - tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::test_discharged_and_non_external_nodes_clean
  - tests/unit/strata/test_circuit_breaker.py::TestMissingCircuitBreaker::test_waiver_on_one_node_keeps_sibling_node_finding
  - tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker::test_declared_with_no_code_evidence_fires
  - tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker::test_declared_with_real_code_evidence_discharges
  - tests/unit/strata/test_circuit_breaker.py::TestUnprovenCircuitBreaker::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
threat: null
component: null
---
Every external dependency node must declare a circuit-breaker/bulkhead policy, extending LINT004 kill-switch. Proof-against-code required per epic PROVABILITY CONSTRAINT.