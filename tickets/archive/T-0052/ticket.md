---
id: T-0052
title: 'strata phase 3: scenarios, crash contracts, atomicity'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0051
parent: T-0047
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/**
- design/litmus/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_crash.py::TestNoHangCheck::test_timeout_shorter_than_restart_bound_fails_closed
- tests/unit/strata/test_atomic.py::TestEvaluateSagaContractsJoin::test_flow_into_coordinator_marked_at_least_once_and_joined
designated_repro_test: null
acceptance:
- text: GIVEN scenario Breach(Gateway) in the payments litmus WHEN frob sys check
    runs THEN blast radius, revocation SLA, and recovery-path-independence verdicts
    are produced
  evidence: []
threat: null
component: null
---
Scenario rewrites (node loss, rate surge, trust downgrade), on-crash contracts with no-hang caller-timeout checks and crash-retry-idempotency join, atomic/saga with cross-store refusal and exhaustive fault-injection test generation from closed ErrorSets.