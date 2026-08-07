---
id: T-0654
title: 'strata: SYNC CALL-CHAIN DEPTH bound obligation'
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
- tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_chain_below_bound_clean
- tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_chain_at_bound_fires
- tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_async_hop_breaks_the_chain
- tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_deep_chain_ok_exemption_discharges
- tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_sync_cycle_is_unbounded_and_fires
- tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_waiver_discharges_finding
designated_repro_test: null
acceptance:
- text: Given a sync call chain exceeding the declared/default depth bound, when checked,
    then the obligation fires
  evidence:
  - tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_chain_below_bound_clean
  - tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_chain_at_bound_fires
  - tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_async_hop_breaks_the_chain
  - tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_deep_chain_ok_exemption_discharges
  - tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_sync_cycle_is_unbounded_and_fires
  - tests/unit/strata/test_sync_depth.py::TestSyncDepth::test_waiver_discharges_finding
threat: null
component: null
---
Bound the depth of synchronous call chains (cascading latency/failure risk), using reachability including non-transitive edges (T-0282).