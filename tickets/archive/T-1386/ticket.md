---
id: T-1386
title: T-1224's lock-granularity test asserts a wall-clock bound and flakes under
  load
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_dup_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_dup_cache.py::TestWriteLockGranularity::test_shared_reader_not_blocked_during_standalone_compute_phase
designated_repro_test: null
acceptance:
- text: GIVEN a heavily loaded machine WHEN the shared-reader test runs THEN it still
    passes, because it asserts ordering rather than a duration
  evidence:
  - tests/unit/test_dup_cache.py::TestWriteLockGranularity::test_shared_reader_not_blocked_during_standalone_compute_phase
threat: null
component: null
---
test_shared_reader_not_blocked_during_standalone_compute_phase asserts acquired_after < (compute_seconds / 2), i.e. a shared lock acquire completing in under 1.0s. It failed at 1.26s during a full xdist coverage run purely because the box was loaded (4 pytest workers plus an agent). The T-1224 lock fix itself is sound -- the measurement is the problem.

A wall-clock bound on a shared runner is inherently flaky. The test should assert the CAUSAL claim it actually means: that the shared reader acquires BEFORE the standalone rebuild's compute phase finishes (have the helper record when compute ended and compare orderings), keeping any absolute duration only as a generous sanity ceiling.