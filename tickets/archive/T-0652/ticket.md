---
id: T-0652
title: 'strata: exactly-once vs at-least-once delivery-semantics declaration on queues'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0651
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
- tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_queue_node_without_delivery_semantics_fires
- tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_invalid_delivery_value_fires
- tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_discharged_and_non_queue_nodes_clean
- tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_waiver_discharges_finding
- tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
designated_repro_test: null
acceptance:
- text: Given a queue node with no delivery-semantics declared, when checked, then
    the obligation fires
  evidence:
  - tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_queue_node_without_delivery_semantics_fires
  - tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_invalid_delivery_value_fires
  - tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_discharged_and_non_queue_nodes_clean
  - tests/unit/strata/test_delivery_semantics.py::TestMissingDeliverySemantics::test_waiver_discharges_finding
  - tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics::test_declared_with_no_code_evidence_fires
  - tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics::test_declared_with_real_code_evidence_discharges
  - tests/unit/strata/test_delivery_semantics.py::TestUnprovenDeliverySemantics::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
threat: null
component: null
---
Every queue node must declare its delivery semantics (exactly-once/at-least-once). Shares the queue-node surface work with the message-schema-version obligation.