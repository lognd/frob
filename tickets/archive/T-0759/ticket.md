---
id: T-0759
title: harden T-0710 overhead test against xdist wall-clock fragility
state: dropped
kind: bug
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/perf/test_hotgraph.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0710's TestStackSampler.test_overhead_under_five_percent measures wall-clock elapsed time (unsampled vs sampled, best-of-3) to assert sampler overhead stays under 5 percent. Under pytest-xdist parallel workers (this repo's default -n auto), concurrent worker contention can inflate wall-clock noise beyond what best-of-3 suppresses, risking flakiness in CI even though the sampler itself is not slow. Fix: mark the test to run serially (a 'serial'/xdist_group marker forcing it off the parallel grid) or relax/parameterize the tolerance for CI, whichever this repo's existing flaky-timing precedent (frob.toml/pytest.ini markers) prefers. Found during T-0710 review round 2.

## Drop reason
- 2026-07-23: exact duplicate of T-0760 (scope strict subset, same test, same fragility); fix landed at 99ba6327 under T-0760 with process_time + xdist-gated tolerance