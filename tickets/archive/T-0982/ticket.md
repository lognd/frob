---
id: T-0982
title: 'derived_state_write_lock reentrancy registry is process-local: ProcessPoolExecutor
  worker deadlocks against main''s SHARED holder'
state: done
kind: bug
origin: agent
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/process/_lock.py
- src/frob/gates/__init__.py
- tests/unit/test_process_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_reentrant_same_mode_in_same_thread
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_reentrant_opposite_mode_raises
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_two_threads_serialize_exclusive
- tests/unit/test_process_lock.py::TestDerivedStateLock::test_shared_locks_do_not_block_each_other
- tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_standalone_rebuild_takes_exclusive
- tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_nested_inside_shared_holder_does_not_deadlock
- tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_concurrent_separate_process_writer_still_blocked
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_independent_process_without_marker_still_blocks
- tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey::test_shared_unresolved_then_nested_write_resolved_does_not_deadlock
- tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey::test_write_resolved_then_nested_shared_unresolved_agrees
designated_repro_test: null
acceptance:
- text: given frob check's main process holding SHARED derived_state_lock, when a
    pool worker runs a gate that takes derived_state_write_lock, then the check completes
    without deadlock (join-timeout regression test)
  evidence:
  - tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes
threat: null
component: null
---
Found by T-0974 while enabling dup enforcement: dup_gate runs in a ProcessPoolExecutor worker while frob check's MAIN process holds the SHARED derived_state_lock for the run; find_clones' derived_state_write_lock consults _process_held_counts, which is process-local, so the forked worker cannot see the parent's holding and issues a real flock(LOCK_EX) that blocks forever against the parent's LOCK_SH (lslocks-confirmed: READ main pid, WRITE* worker pid, same .frob/derived.lock, 200+s zero CPU). This is the cross-process sibling of T-0933's path-spelling bug. Fix directions: pass a held-lock signal into pool workers explicitly (initializer arg or env marker set by the pool owner), or have workers request the write lock in non-blocking mode with a documented fallback, or move exclusive acquisition to the pool OWNER before dispatch. The T-0918 test suite plus a new pool-worker regression (spawn a real worker under a parent SHARED holder with a join timeout) must pass. T-0974 (dup enforce default) is blocked on this.