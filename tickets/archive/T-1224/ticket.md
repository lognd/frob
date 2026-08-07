---
id: T-1224
title: 'bug: clones stage serializes on exclusive derived_state_write_lock -- concurrent
  frob stalls dup pipeline'
state: done
kind: bug
origin: agent
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/process/_lock.py
- src/frob/dup/**
- docs/modules/dup.md
- tests/unit/test_dup_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/dup.md
  reason: 'T-1224: doc update for the locking-granularity change (docs/modules/dup.md)
    and a new regression test proving the fix (tests/unit/test_dup_cache.py)'
  actor: logan
  at: '2026-08-01'
- op: add
  glob: tests/unit/test_dup_cache.py
  reason: 'T-1224: doc update for the locking-granularity change (docs/modules/dup.md)
    and a new regression test proving the fix (tests/unit/test_dup_cache.py)'
  actor: logan
  at: '2026-08-01'
evidence:
- tests/unit/test_dup_cache.py::TestWriteLockGranularity::test_shared_reader_not_blocked_during_standalone_compute_phase
- tests/unit/test_dup_cache.py::TestFingerprintRoundTrip::test_put_then_get_returns_same_payload
- tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_concurrent_separate_process_writer_still_blocked
- tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_evicts_lru_rows_beyond_cache_entries
designated_repro_test: null
acceptance:
- text: GIVEN the clones profile observed a 240s fcntl.flock wait on derived_state_write_lock
    (src/frob/process/_lock.py:372) caused by a concurrent frob process contending
    for .frob derived-state writes WHEN the dup pipeline's locking is made finer-grained
    or read-shared (design decides the mechanism) THEN concurrent frob invocations
    (e.g. a sweep and a second check) do not block each other's clones stage on derived-state
    writes for the full stage duration
  evidence:
  - tests/unit/test_dup_cache.py::TestWriteLockGranularity::test_shared_reader_not_blocked_during_standalone_compute_phase
  - tests/unit/test_dup_cache.py::TestFingerprintRoundTrip::test_put_then_get_returns_same_payload
  - tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_concurrent_separate_process_writer_still_blocked
  - tests/unit/test_dup_cache.py::TestVerdictRoundTrip::test_put_verdict_evicts_lru_rows_beyond_cache_entries
threat: null
component: null
---
Root cause: src/frob/process/_lock.py:372 derived_state_write_lock is a single exclusive flock guarding the dup pipeline's derived-state writes; any concurrent frob process (sweep, second check) contending for it stalls the clones stage for its entire duration -- observed as a 240s flock wait during profiling (excluded from the report's compute shares as an artifact of concurrent profiling, but the underlying serialization is real and reproducible under any real concurrent frob usage). Fix: finer-grained locking (e.g. per-file or per-shard) or a read-shared lock mode for readers, design TBD.