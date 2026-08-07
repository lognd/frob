## Done report

Cross-process sibling of T-0933: a pool worker's empty process-local reentrancy registry issued a real blocking LOCK_EX against its own pool owner's LOCK_SH. Fix: _open_process_pool stamps held_registry_keys() into FROB_DERIVED_LOCK_HELD_KEYS before pool construction (T-0806 env-marker pattern); a worker's derived_state_write_lock treats a matching canonical root key as an inherited hold and bypasses acquisition exactly like the same-process nested case, while independent processes still take real exclusive locks. Proven by a real spawn-context pool worker under a parent SHARED holder completing inside a 15s join timeout.

### Changed
```
 docs/modules/process.md         |  27 +++
 src/frob/gates/__init__.py      |  24 ++-
 src/frob/process/_lock.py       | 146 +++++++++++--
 tests/unit/test_process_lock.py | 112 ++++++++++
 tickets.md                      | 446 +++++++++++++++++++++++++++++++++++++++-
 5 files changed, 736 insertions(+), 19 deletions(-)
```

### Evidence
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_lock_file_created_under_frob_dir` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_reentrant_same_mode_in_same_thread` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_reentrant_opposite_mode_raises` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_two_threads_serialize_exclusive` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateLock::test_shared_locks_do_not_block_each_other` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_standalone_rebuild_takes_exclusive` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_nested_inside_shared_holder_does_not_deadlock` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_concurrent_separate_process_writer_still_blocked` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_independent_process_without_marker_still_blocks` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey::test_shared_unresolved_then_nested_write_resolved_does_not_deadlock` (pytest node id, verified passing when recorded)
- `tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey::test_write_resolved_then_nested_shared_unresolved_agrees` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
