---
id: T-0694
title: 'lock-ordering graph: cyclic acquisition order across call paths = potential-deadlock
  finding'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: medium
parent: T-0693
tier: ticket
sprint: null
scope:
- src/frob/arch/**
- tests/unit/test_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
- tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_across_call_paths_via_callees
- tests/unit/test_arch.py::TestLockOrderingHazards::test_consistent_global_order_does_not_fire
- tests/unit/test_arch.py::TestLockOrderingHazards::test_reentrant_same_lock_does_not_fire
- tests/unit/test_arch.py::TestLockOrderingHazards::test_unresolvable_lock_identity_is_advisory
designated_repro_test: null
acceptance:
- text: GIVEN two functions acquiring locks A-then-B and B-then-A WHEN the check runs
    THEN a finding names both call paths; GIVEN consistent global ordering THEN silence
  evidence:
  - tests/unit/test_arch.py::TestLockOrderingHazards.test_two_lock_ab_ba_cycle_fires_within_one_function
  - tests/unit/test_arch.py::TestLockOrderingHazards.test_two_lock_ab_ba_cycle_fires_across_call_paths_via_callees
  - tests/unit/test_arch.py::TestLockOrderingHazards.test_consistent_global_order_does_not_fire
  - tests/unit/test_arch.py::TestLockOrderingHazards.test_reentrant_same_lock_does_not_fire
  - tests/unit/test_arch.py::TestLockOrderingHazards.test_unresolvable_lock_identity_is_advisory
  - tests/unit/test_arch.py::TestLockOrderingHazards::test_two_lock_ab_ba_cycle_fires_within_one_function
threat: null
component: null
---
Child 1 of T-0693. Track with-statement (and explicit acquire/release) nesting of statically-identifiable lock objects (module/class-level threading.Lock/RLock/Semaphore, multiprocessing locks, anyio/asyncio locks); build the acquisition-order graph across call paths via the call graph; a cycle = potential deadlock naming both paths and both locks. Unresolvable lock identity -> advisory-tier note, fail-closed philosophy without drowning signal. Fixtures: the classic AB/BA two-lock deadlock fires; single global lock ordering does not.