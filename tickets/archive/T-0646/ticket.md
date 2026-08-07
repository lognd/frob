---
id: T-0646
title: 'strata: BACKPRESSURE bounded-intake obligation on queues/consumers'
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
- tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_queue_node_without_bounded_intake_fires
- tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_consumer_node_without_bounded_intake_fires
- tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_discharged_and_non_queue_nodes_clean
- tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_waiver_discharges_finding
- tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
acceptance:
- text: Given a queue/consumer node with no bounded-intake policy declared, when checked,
    then the obligation fires
  evidence:
  - tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_queue_node_without_bounded_intake_fires
  - tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_consumer_node_without_bounded_intake_fires
  - tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_discharged_and_non_queue_nodes_clean
  - tests/unit/strata/test_backpressure.py::TestMissingBoundedIntake::test_waiver_discharges_finding
  - tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_code_evidence_fires
  - tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_real_code_evidence_discharges
  - tests/unit/strata/test_backpressure.py::TestUnprovenBoundedIntake::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
threat: null
component: null
---
Every queue/consumer node must declare bounded intake (backpressure policy), extending LINT003 surge / LINT005 capacity.