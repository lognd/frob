---
id: T-0760
title: harden T-0710 hot-graph overhead test against xdist wall-clock fragility
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0710
tier: ticket
sprint: null
scope:
- tests/unit/perf/
- src/frob/perf/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent
designated_repro_test: null
acceptance:
- text: GIVEN the overhead test WHEN the full suite runs under -n auto THEN it passes
    reliably (serial marker, CPU-time measure, or documented-tolerance margin), not
    only under -n0
  evidence:
  - tests/unit/perf/test_hotgraph.py::TestStackSampler::test_overhead_under_five_percent
threat: null
component: null
---
From T-0710: the hot-graph overhead test (attribution sampler <5% overhead) asserts a hard <5% on a ~0.11s workload = ~5.5ms margin, best-of-3 min-vs-min. Under pytest-xdist (-n auto, the default) the baseline and sampled loops compete with 11 concurrent workers for cores -- reproduced live: the test FAILS under -n auto, passes -n0. Harden it: either mark it serial (a no-xdist / serial marker so it runs alone), or relax the CI margin with a documented tolerance, or switch to a CPU-time (not wall-clock) measure immune to core contention. Pick the robust option and document why.