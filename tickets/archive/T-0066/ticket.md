---
id: T-0066
title: 'strata capacity arithmetic: utilization, fanout, skew, growth horizons'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0050
parent: T-0051
tier: ticket
sprint: null
scope:
- docs/strata/**
- tickets.md
- strata-core/**
- Makefile
- .github/**
- design/litmus/**
- src/frob/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_capacity.py::TestSkewUtilization::test_skew_refutes_where_mean_would_prove
- tests/unit/strata/test_capacity.py::TestGrowthHorizon::test_growth_flips_proved_to_refuted_with_month_count
- tests/unit/strata/test_capacity.py::TestPropagatedDemand::test_positive_rate_cycle_is_unbounded
designated_repro_test: null
threat: null
component: null
---
Demand propagation with fanout multipliers and zipf skew (check hottest shard, not mean); cold/degraded modes; saturation-date diagnostics; measured capacities bind to frob.perf stamps.