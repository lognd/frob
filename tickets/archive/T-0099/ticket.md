---
id: T-0099
title: document demand() behavior shift for unresolvable rates (propagates vs drops)
state: done
kind: docs
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/strata/**
- src/frob/strata/**
- tests/unit/strata/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_capacity.py::TestPropagatedDemand::test_unresolvable_rate_propagates_upstream_demand
designated_repro_test: null
threat: null
component: null
---
T-0066 reviewer finding: flows whose rate.base_value() errors were previously dropped from demand sums; propagated_demand now treats them as undeclared and recurses into upstream demand. Probably more correct (fails toward propagating load) but undocumented; document in kernel.md capacity semantics or revert deliberately.