---
id: T-0072
title: strata tube + chirp litmus models + goldens
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
- design/litmus/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_tube.py::TestTubeGoldens::test_payout_age_bound_refutes_off_the_approximate_counter_path
- tests/unit/strata/test_litmus_chirp.py::TestChirpGoldens::test_hottest_shard_utilization_refutes_under_zipf_skew
- tests/unit/strata/test_litmus_chirp.py::TestChirpGoldens::test_growth_horizon_flips_a_passing_utilization_to_refuted
designated_repro_test: null
threat: null
component: null
---
Tube: stampede/cold-cache, immutable-TTL pairing, CDN declassification, payout-vs-approximate-counter. Chirp: fanout write ceiling under zipf skew forcing the hybrid. Phase-2 exit criterion.