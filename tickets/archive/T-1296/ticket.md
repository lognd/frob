---
id: T-1296
title: 'TEST005 burn-down: src/frob/strata (196 findings, 1 at 0.0%)'
state: dropped
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1273
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_atomic.py::TestJoinSagaIdempotencyNoCoordinators::test_empty_coordinator_ids_returns_model_unchanged
- tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsFactsError::test_build_facts_error_is_propagated
- tests/unit/strata/test_atomic.py::TestEvaluateAtomicContractsSagaError::test_saga_error_short_circuits_before_fault_injection
- tests/unit/strata/test_breach.py::TestContainmentBounds::test_dimension_mismatched_bounds_fail_closed_with_unit_mismatch
- tests/unit/strata/test_breach.py::TestBreachContractsFactsAndScenarioErrors::test_build_facts_error_propagates_out_of_blast_radius
- tests/unit/strata/test_breach.py::TestBreachContractsFactsAndScenarioErrors::test_scenario_evaluation_error_propagates
- tests/unit/strata/test_distributed_txn.py::TestMultiServiceWritersSelfLoop::test_self_loop_flow_is_excluded_from_written_node_set
- tests/unit/strata/test_distributed_txn.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_design_load.py::TestLoadIds::test_unreadable_file_reported_as_parse_failed
- tests/unit/strata/test_design_load.py::TestLoadIds::test_elaborate_failure_reported_with_store_ids_and_resources_intact
- tests/unit/strata/test_design_load.py::TestUnbound::test_kind_with_zero_ids_contributes_nothing_and_outer_loop_continues
- tests/unit/strata/test_design_load.py::TestUnbound::test_edge_of_an_uninteresting_kind_is_skipped
- tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_non_access_attr_amid_access_attrs_is_skipped
- tests/unit/strata/test_clock_ordering.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_delivery_semantics.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_retry.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_backpressure.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_circuit_breaker.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_fallback.py::TestBindCodeErrorPropagation::test_ambiguous_code_binding_error_propagates
- tests/unit/strata/test_deploy.py::TestScenarioEvaluationErrorPropagation::test_evaluate_scenarios_error_propagates
designated_repro_test: null
acceptance:
- text: GIVEN the strata package at the 75%/70% floors WHEN frob check --only test
    runs THEN it reports 0 TEST005 findings under src/frob/strata/**
  evidence: []
- text: GIVEN a 0.0%-branch symbol in strata WHEN it is judged dead code THEN it is
    routed to the DEAD gate/dup machinery or a removal ticket, never given an assert-True
    filler test
  evidence: []
- text: GIVEN a new test added to close a strata TEST005 finding WHEN reviewed THEN
    it asserts real behavior (inputs/outputs/side effects), not mere import/instantiation
  evidence:
  - tests/unit/strata/test_atomic.py::TestJoinSagaIdempotencyNoCoordinators::test_empty_coordinator_ids_returns_model_unchanged
  - tests/unit/strata/test_breach.py::TestContainmentBounds::test_dimension_mismatched_bounds_fail_closed_with_unit_mismatch
  - tests/unit/strata/test_distributed_txn.py::TestMultiServiceWritersSelfLoop::test_self_loop_flow_is_excluded_from_written_node_set
  - tests/unit/strata/test_design_load.py::TestLoadIds::test_unreadable_file_reported_as_parse_failed
  - tests/unit/strata/test_access.py::TestNodeAccessDeclarations::test_non_access_attr_amid_access_attrs_is_skipped
threat: null
component: null
---
Package: src/frob/strata (or the listed root modules).
TEST005 findings at current baseline: 196 total, 1 at exactly
0.0% branch coverage (the priority tier -- dead-code or untested-entry-
point candidates; judge each before writing a test).

0.0%-branch symbols in this package:
_selfconform.py :: check_self_conformance

Work: for each finding, either (a) add a real behavioral test that
exercises the branch/line paths (never assert-True filler, never a test
that only imports the module), or (b) if a 0.0% symbol is confirmed dead
(no live caller, no CLI/API entry point), route it to the DEAD gate / dup
machinery or file a removal ticket instead of writing a fake test for it
-- do not fabricate coverage.

## Drop reason
- 2026-08-02: superseded by its own delivered-portion split: T-1414 landed the 12 genuine-gap modules (done), and T-1415 carries the honest remainder as a queued ticket; keeping T-1296 in-progress alongside T-1415 double-counts the same work