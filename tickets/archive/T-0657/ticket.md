---
id: T-0657
title: 'strata: clock/ordering-assumptions obligation across distributed flows'
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
- tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy::test_clock_dependent_flow_without_ordering_strategy_fires
- tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy::test_discharged_and_non_clock_dependent_flows_clean
- tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy::test_waiver_discharges_finding
- tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy::test_declared_with_no_code_evidence_fires
- tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy::test_declared_with_real_code_evidence_discharges
- tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/strata/test_clock_ordering.py::TestWallClockOnly::test_bare_wall_clock_read_fires_rel372
designated_repro_test: null
acceptance:
- text: Given a cross-node flow with an implicit clock/ordering assumption and no
    declared strategy, when checked, then the obligation fires
  evidence:
  - tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy::test_clock_dependent_flow_without_ordering_strategy_fires
  - tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy::test_discharged_and_non_clock_dependent_flows_clean
  - tests/unit/strata/test_clock_ordering.py::TestMissingOrderingStrategy::test_waiver_discharges_finding
  - tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy::test_declared_with_no_code_evidence_fires
  - tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy::test_declared_with_real_code_evidence_discharges
  - tests/unit/strata/test_clock_ordering.py::TestUnprovenOrderingStrategy::test_declared_with_no_bound_code_is_uncheckable_not_a_violation
  - tests/unit/strata/test_clock_ordering.py::TestWallClockOnly::test_bare_wall_clock_read_fires_rel372
threat: null
component: null
---
Flag flows relying on wall-clock ordering/synchronization assumptions across distributed nodes without a declared clock/ordering strategy (T-0282 reachability).