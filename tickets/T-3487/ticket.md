---
id: T-3487
title: 'test_with_serial_pools_worker_is_majority_attributed: relative assertion from
  T-3455 rejects 0.998 vs 0.504'
state: queued
kind: bug
origin: agent
created: '2026-08-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/perf/test_serial_pools.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on GitHub Actions run 33308245923 (ubuntu-latest, HEAD 355eb4468, 2026-08-30): suite completed in 16.3 min with 6 failures of 12816. Reproduce by node id with -p no:xdist first.

FAILING: tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_with_serial_pools_worker_is_majority_attributed
    AssertionError: patched attribution (0.9978) was not decisively larger than unpatched attribution (0.5039) measured in the same run
0.998 vs 0.504 IS decisively larger, so the relative assertion T-3455 introduced is mis-stated (inverted operands, a ratio threshold above 2x, or comparing the wrong pair). Fix the assertion so it states the property (patched attribution exceeds unpatched by a clear margin, e.g. ratio >= 1.5 AND patched > 0.9) and add the failing numbers to the message. Run 5x.
