---
id: T-0693
title: 'concurrency hazard analysis: structural deadlock/race/event-loop checks +
  model-mismatch advisory (parent)'
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- src/frob/gates/**
- docs/design/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
- tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool
- tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_fires_on_time_sleep
- tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
- tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound
designated_repro_test: null
acceptance:
- text: GIVEN the children closed WHEN frob check runs on fixtures reproducing each
    hazard class THEN each fires per its own acceptance
  evidence:
  - tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
  - tests/unit/test_arch.py::TestForkPoolHazards::test_pool_inside_pool_fires_on_process_pool_alongside_thread_pool
  - tests/unit/test_arch.py::TestAsyncEventLoopHazards::test_blocking_call_in_async_fires_on_time_sleep
  - tests/unit/test_arch.py::TestSharedStateRaceHazards::test_unguarded_write_from_thread_submitted_function_fires
  - tests/unit/test_arch.py::TestConcurrencyModelMismatch::test_cpu_bound_loop_in_threadpool_fires_gil_bound
threat: null
component: null
---
User mandate 2026-07-22: static checks for multiprocessing/threading/async code. Not a soundness claim -- a STRUCTURAL may-analysis over the call graph + normalized model (T-0609..T-0612) catching the classes that actually bite, fail-closed on opaque dispatch per T-0339 doctrine. Field motivation from this very session: the ProcessPoolExecutor-inside-ThreadPoolExecutor deadlock (T-0265 disclosure, T-0581 structural fix, T-0692 CI guard) ate a 6h CI job. Children: lock-order graph, fork/pool structural hazards, async event-loop hazards, shared-mutable-state approximation, IO/CPU-bound model-mismatch advisory. Umbrella closes when children close.