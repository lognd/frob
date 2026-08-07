---
id: T-0075
title: 'strata atomic/saga: cross-store refusal + fault-injection generation'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0051
parent: T-0052
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsNoSaga::test_empty_diagnostics_when_no_coordinator_declared
- tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsJoin::test_flow_into_coordinator_marked_at_least_once_and_joined
- tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsJoin::test_flow_into_idempotent_coordinator_produces_no_diagnostic
- tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsJoin::test_already_at_least_once_flow_is_not_double_marked
- tests/unit/strata/test_atomic.py::TestGenerateFaultInjectionCases::test_strong_guarantee_operation_generates_one_case_per_variant
- tests/unit/strata/test_atomic.py::TestGenerateFaultInjectionCases::test_nonempty_err_frame_operation_is_not_eligible
- tests/unit/strata/test_atomic.py::TestGenerateFaultInjectionCases::test_operation_missing_from_error_sets_generates_nothing
- tests/unit/strata/test_atomic.py::TestEvaluateAtomicContracts::test_joins_saga_diagnostics_and_fault_injection_cases
- tests/unit/strata/test_atomic.py::TestEvaluateAtomicContracts::test_defaults_to_no_fault_injection_cases_without_error_sets
designated_repro_test: null
threat: null
component: null
---
modifies {} on Err via stage-commit (infallible-commit decidable from Result graph), immutable swap, tx chokepoint, WAL; atomic claims spanning stores refused without saga/2PC; generated exhaustive fault-injection property tests from closed ErrorSets.