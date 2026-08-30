---
id: T-3455
title: test_without_serial_pools_worker_is_unattributed asserts an absolute wall-clock
  bound that CI runners miss
state: queued
kind: bug
origin: agent
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/perf/test_serial_pools.py
- src/frob/perf/_harness.py
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
MEASURED on GitHub Actions run 33282540898 (ubuntu-latest, HEAD b94cea5d0, 2026-08-30) -- the first run that completed to 100% (20 failures of 12689). This failure is in the cross-platform set (fails on macOS too unless noted). Reproduce locally by node id with -p no:xdist first; if it passes locally, the defect is an environment dependency (git identity, tmp path shape, missing tool, timing) and the fix must make the test hermetic, not skip it.

FAILING: tests/unit/perf/test_serial_pools.py::TestInstallSerialPools::test_without_serial_pools_worker_is_unattributed
    assert 0.5013780752997159 < 0.2
A wall-clock threshold on a shared CI runner. Replace the absolute timing assertion with a relative one (ratio against a measured baseline in the same test) or with a structural assertion about attribution, so the test states the property, not a machine speed.
