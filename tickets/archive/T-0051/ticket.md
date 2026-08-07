---
id: T-0051
title: 'strata phase 2: std.infra + bounds + policy forms + boundaries'
state: done
kind: feature
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0050
parent: T-0047
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/**
- design/litmus/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_tube.py::TestTubeGoldens::test_payout_age_bound_refutes_off_the_approximate_counter_path
- tests/unit/strata/test_litmus_chirp.py::TestChirpGoldens::test_hottest_shard_utilization_refutes_under_zipf_skew
designated_repro_test: null
acceptance:
- text: GIVEN tube.strata and chirp.strata WHEN frob sys check runs THEN stampede,
    fanout-ceiling, staleness, and CDN-declassification findings fire per goldens
  evidence: []
threat: null
component: null
---
store/cache/queue/cdn elaboration with mandatory invalidation edges, unified age/staleness propagation, capacity arithmetic with skew + growth horizons + cold/degraded modes, the 5 policy forms with semantic scoping + enables cascade, std.policy.analyzable, six-phase boundary contract with outcome-conditioned frames, errors-total/panics-contained/observe packs. See docs/strata/{policy,boundary}.md.