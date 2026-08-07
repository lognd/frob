---
id: T-0645
title: 'strata: SPOF detection - inbound-critical-flow node with replicas_max=1/no
  redundancy'
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
- tests/unit/strata/test_spof.py::TestSpof::test_singleton_node_with_critical_inbound_fires
- tests/unit/strata/test_spof.py::TestSpof::test_declared_singleton_capacity_fires
- tests/unit/strata/test_spof.py::TestSpof::test_replicated_capacity_clean
- tests/unit/strata/test_spof.py::TestSpof::test_redundant_exemption_clean
- tests/unit/strata/test_spof.py::TestSpof::test_non_critical_flow_clean
- tests/unit/strata/test_spof.py::TestSpof::test_waiver_on_one_node_keeps_sibling_node_finding
designated_repro_test: null
acceptance:
- text: Given a node with inbound critical flows and replicas_max=1, when checked,
    then SPOF obligation fires unless waived
  evidence:
  - tests/unit/strata/test_spof.py::TestSpof::test_singleton_node_with_critical_inbound_fires
  - tests/unit/strata/test_spof.py::TestSpof::test_declared_singleton_capacity_fires
  - tests/unit/strata/test_spof.py::TestSpof::test_replicated_capacity_clean
  - tests/unit/strata/test_spof.py::TestSpof::test_redundant_exemption_clean
  - tests/unit/strata/test_spof.py::TestSpof::test_non_critical_flow_clean
  - tests/unit/strata/test_spof.py::TestSpof::test_waiver_on_one_node_keeps_sibling_node_finding
threat: null
component: null
---
A node receiving critical inbound flows with replicas_max=1 or no declared redundancy is a single point of failure; flag as a hard obligation, deny-by-default with reasoned waive (T-0174).