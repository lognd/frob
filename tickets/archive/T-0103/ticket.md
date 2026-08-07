---
id: T-0103
title: std.infra drops declared store capacity (UTILIZATION can never target a store)
state: done
kind: bug
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/**
- docs/strata/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_infra.py::TestStoreCapacity::test_store_capacity_maps_through_to_the_kernel_node
designated_repro_test: null
threat: null
component: null
---
T-0072 litmus gap report: store { capacity N unit replicas A..B } parses, but _infra.py::_elaborate_store hardcodes capacity=None, so utilization claims on stores always refute 'declares no capacity'. Map the surface capacity through to the kernel Node exactly as _elaborate.py does for NodeDecl.