---
id: T-0703
title: 'strata starvation/throughput obligations: serialization-point utilization,
  writer starvation, unbounded waits'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
blocked_by:
- T-0700
- T-0702
parent: T-0331
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/
- docs/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/strata/**
  reason: 'REL38x obligation family docs (docs/strata/reliability.md section, docs/strata/waive.md
    MULTI_INSTANCE_WAIVER_FAMILIES table update) are required by the obligation-family
    pattern this ticket follows -- every sibling family (T-0645/T-0646/T-0700/T-0702)
    documents its rules in these same two files.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/strata/test_starvation.py::TestUtilization::test_over_capacity_demand_fires_with_arithmetic
- tests/unit/strata/test_starvation.py::TestUtilization::test_declared_capacity_within_bounds_is_clean
- tests/unit/strata/test_starvation.py::TestUtilization::test_undeclared_demand_fails_closed
- tests/unit/strata/test_starvation.py::TestUtilization::test_arbitrated_by_node_is_the_serialization_point
- tests/unit/strata/test_starvation.py::TestUtilization::test_read_only_accessor_is_not_a_serialization_point
- tests/unit/strata/test_starvation.py::TestWriterStarvation::test_read_heavy_writer_with_no_alpha_fires_advisory
- tests/unit/strata/test_starvation.py::TestWriterStarvation::test_alpha_accessor_discharges
- tests/unit/strata/test_starvation.py::TestUnboundedWait::test_contended_write_access_with_no_timeout_fires
- tests/unit/strata/test_starvation.py::TestUnboundedWait::test_declared_timeout_discharges
- tests/unit/strata/test_starvation.py::TestUnboundedWait::test_lone_accessor_is_not_contended
designated_repro_test: null
acceptance:
- text: GIVEN 500k declared users flowing to a db with mode=exclusive and default
    holding time WHEN sys checks run THEN a utilization error fires showing the arithmetic;
    GIVEN the same db with demand undeclared THEN a fail-closed demand-undeclared
    finding; GIVEN a read-preferring lock with no alpha/fairness on a read-heavy resource
    THEN a writer-starvation advisory
  evidence:
  - tests/unit/strata/test_starvation.py::TestUtilization::test_over_capacity_demand_fires_with_arithmetic
threat: null
component: null
---
User mandate 2026-07-22: the 500k-users-vs-exclusive-write-lock case. Three obligation families over the T-0700 modes + demand grammar: (1) SERIALIZATION-POINT UTILIZATION: every effective-concurrency-1 point (exclusive mode, single arbiter, alpha-gated writer path) compares aggregate inbound demand x holding-time hint against capacity; over threshold = SYS error SHOWING THE ARITHMETIC in the finding (demand, holding time, resulting utilization/wait), not a vibe; an exclusive/arbitered resource with UNDECLARED upstream demand fails closed with demand-undeclared (the check cannot be silently skipped). Coordinate with T-0645 (SPOF -- a saturated single arbiter is quantitative SPOF) and T-0646 (backpressure -- what bounds the queue at the serialization point). (2) WRITER STARVATION policy: read-heavy resource whose declared lock discipline lets readers perpetually preempt the writer (plain RW preference, no alpha or fair-queuing declaration) = advisory recommending alpha (T-0700) or fair queuing, even at low utilization. (3) UNBOUNDED WAIT: lock/arbiter acquisition on a contended resource with no declared timeout joins the T-0640 timeout obligation family. Litmus fixtures per family, firing and clean.