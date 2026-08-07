---
id: T-0656
title: 'strata: no-shared-mutable-state-across-service-boundaries obligation'
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
- tests/unit/strata/test_shared_state.py::TestSharedState::test_mutable_node_shared_by_two_services_fires
- tests/unit/strata/test_shared_state.py::TestSharedState::test_read_only_accessor_still_fires
- tests/unit/strata/test_shared_state.py::TestSharedState::test_single_writer_clean
- tests/unit/strata/test_shared_state.py::TestSharedState::test_immutable_node_touched_by_many_is_clean
- tests/unit/strata/test_shared_state.py::TestSharedState::test_shared_state_ok_exemption_discharges
- tests/unit/strata/test_shared_state.py::TestSharedState::test_owner_attr_alone_does_not_discharge
- tests/unit/strata/test_shared_state.py::TestSharedState::test_waiver_discharges_finding
designated_repro_test: null
acceptance:
- text: Given two services sharing a mutable store/memory region across their boundary
    with no declared exception, when checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_shared_state.py::TestSharedState::test_mutable_node_shared_by_two_services_fires
  - tests/unit/strata/test_shared_state.py::TestSharedState::test_read_only_accessor_still_fires
  - tests/unit/strata/test_shared_state.py::TestSharedState::test_single_writer_clean
  - tests/unit/strata/test_shared_state.py::TestSharedState::test_immutable_node_touched_by_many_is_clean
  - tests/unit/strata/test_shared_state.py::TestSharedState::test_shared_state_ok_exemption_discharges
  - tests/unit/strata/test_shared_state.py::TestSharedState::test_owner_attr_alone_does_not_discharge
  - tests/unit/strata/test_shared_state.py::TestSharedState::test_waiver_discharges_finding
threat: null
component: null
---
Detect and flag shared mutable state reachable across a declared service boundary.