---
id: T-1414
title: 'strata TEST005: close the 12 modules with genuine branch gaps (T-1296 delivered
  portion)'
state: done
kind: feature
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsNoSaga::test_empty_diagnostics_when_no_coordinator_declared
- tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsJoin::test_flow_into_coordinator_marked_at_least_once_and_joined
designated_repro_test: null
acceptance:
- text: GIVEN the twelve named strata modules WHEN each is measured standalone with
    pytest --cov --cov-branch THEN each reports 100 percent branch coverage
  evidence:
  - tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsNoSaga::test_empty_diagnostics_when_no_coordinator_declared
  - tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsJoin::test_flow_into_coordinator_marked_at_least_once_and_joined
- text: GIVEN each added test WHEN reviewed THEN it asserts real behaviour on a branch
    confirmed unexercised beforehand, never an import-only or assert-True filler
  evidence:
  - tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsNoSaga::test_empty_diagnostics_when_no_coordinator_declared
  - tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsJoin::test_flow_into_coordinator_marked_at_least_once_and_joined
threat: null
component: null
---
Carries the completed, verified portion of T-1296's work to main. T-1296 itself stays open against its true goal.

WHY A SEPARATE TICKET RATHER THAN CLOSING T-1296. T-1296's acceptance criterion [0] reads "0 TEST005 findings under src/frob/strata/**" across a package with 196 findings. No single dispatch can satisfy that, so the ticket is unclosable by construction, and with T-1410's gate-claim guard now wired, frob ticket land correctly refuses it. Weakening that criterion to force a close would be the exact false-close T-1399/T-1410 exist to prevent. So the criterion stands untouched and unmet, and this ticket describes only what was actually delivered.

DELIVERED. Twelve strata modules brought to 100 percent branch coverage standalone, verified per module with pytest --cov=<module> --cov-branch: _atomic, _breach, _distributed_txn, _design_load, _access, _clock_ordering, _delivery_semantics, _retry, _backpressure, _circuit_breaker, _fallback, _deploy.

The targeted branches were error-path propagation (bind_code/build_facts/evaluate_scenarios returning Err), early-return guards, loop skip-arms, and dimension-mismatch/unreadable-file/self-loop edges. Every one was confirmed genuinely unexercised BEFORE a test was written -- no test was added to a branch that was already covered, which moves no real number and is the filler this drive explicitly forbids.

INVESTIGATED AND DELIBERATELY NOT TOUCHED. _selfconform.py::check_self_conformance, the package's one 0.0 percent symbol, already carries 67 real assertions and measures 95 percent standalone. Its 0.0 percent reading was a measurement artifact, and it is not dead code -- live callers exist in gates/_sys.py, _native_test.py and app/sys_runner.py. Writing a test for it would have been filler against already-tested code.

REMAINDER, tracked by T-1296 and not by this ticket: roughly 23 strata modules still carry real partial-coverage gaps (_claims 54 percent, _elaborate 49 percent, _audit 88 percent, _compliance 89 percent, and others).