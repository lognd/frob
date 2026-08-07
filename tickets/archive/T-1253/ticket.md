---
id: T-1253
title: 'ledger v2: per-ticket lock + allocator lock primitives'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1136
tier: ticket
sprint: null
scope:
- src/frob/process/_lock.py
- src/frob/tickets/_store.py
- tests/unit/test_process_lock.py
- tests/test_tickets_ledger_concurrency.py
- docs/design/ledger-v2.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/ledger-v2.md
  reason: T-1253 adds an implementation-status note to this design doc's own section
    3
  actor: logan
  at: '2026-07-29'
- op: add
  glob: design/frob.strata
  reason: auto-synced test-registry interface entries (TestAllocatorLock/TestTicketLock)
    added by this ticket's own new test classes
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_process_lock.py::TestTicketLock::test_lock_path_is_per_ticket_id
- tests/unit/test_process_lock.py::TestTicketLock::test_two_different_ticket_ids_do_not_block_each_other
- tests/unit/test_process_lock.py::TestTicketLock::test_same_id_from_two_threads_serializes
- tests/unit/test_process_lock.py::TestTicketLock::test_reentrant_same_id_in_same_thread_does_not_deadlock
- tests/unit/test_process_lock.py::TestAllocatorLock::test_lock_file_created_under_frob_dir
- tests/unit/test_process_lock.py::TestAllocatorLock::test_two_concurrent_allocations_get_distinct_ids
- tests/unit/test_process_lock.py::TestAllocatorLock::test_reentrant_in_same_thread_does_not_deadlock
designated_repro_test: null
acceptance:
- text: 'Ledger v2 design (docs/design/ledger-v2.md section 3) needs a per-ticket

    file lock plus a single tiny allocator lock, replacing the one repo-wide

    `ledger_lock` that serializes every ticket-mutating verb today regardless

    of which ticket(s) they touch. Generalizes the T-0933/T-0982 fix (a

    process-registry reentrancy bug caused by one shared contended resource)

    by removing the shared resource for the common case (one verb, one

    ticket).'
  evidence:
  - tests/unit/test_process_lock.py::TestTicketLock::test_lock_path_is_per_ticket_id
- text: 'Deliverables: a `ticket_lock(root, ticket_id)` context manager (per-ticket

    flock, e.g. `tickets/T-####/.lock` or an flock on `ticket.md` itself) and

    a separate `allocator_lock(root)` guarding only next-id computation. Both

    must compose safely with the existing `ledger_lock` during the

    compatibility window (section 7) -- do not remove `ledger_lock` yet, this

    ticket only ADDS the new primitives alongside it.'
  evidence:
  - tests/unit/test_process_lock.py::TestTicketLock::test_lock_path_is_per_ticket_id
  - tests/unit/test_process_lock.py::TestTicketLock::test_two_different_ticket_ids_do_not_block_each_other
  - tests/unit/test_process_lock.py::TestTicketLock::test_same_id_from_two_threads_serializes
  - tests/unit/test_process_lock.py::TestTicketLock::test_reentrant_same_id_in_same_thread_does_not_deadlock
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_lock_file_created_under_frob_dir
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_two_concurrent_allocations_get_distinct_ids
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_reentrant_in_same_thread_does_not_deadlock
- text: 'GIVEN two callers each hold `ticket_lock` for different ticket ids

    WHEN both proceed concurrently

    THEN neither blocks the other (verified with a real concurrent-thread

    test, not just code inspection).'
  evidence:
  - tests/unit/test_process_lock.py::TestTicketLock::test_lock_path_is_per_ticket_id
  - tests/unit/test_process_lock.py::TestTicketLock::test_two_different_ticket_ids_do_not_block_each_other
  - tests/unit/test_process_lock.py::TestTicketLock::test_same_id_from_two_threads_serializes
  - tests/unit/test_process_lock.py::TestTicketLock::test_reentrant_same_id_in_same_thread_does_not_deadlock
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_lock_file_created_under_frob_dir
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_two_concurrent_allocations_get_distinct_ids
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_reentrant_in_same_thread_does_not_deadlock
- text: 'GIVEN two callers both call the id allocator concurrently

    WHEN both request a next id

    THEN they receive distinct ids (interleaving regression test, mirroring

    T-1090''s `test_two_concurrent_finalize_draft_calls_get_distinct_ids`

    shape).'
  evidence:
  - tests/unit/test_process_lock.py::TestTicketLock::test_lock_path_is_per_ticket_id
  - tests/unit/test_process_lock.py::TestTicketLock::test_two_different_ticket_ids_do_not_block_each_other
  - tests/unit/test_process_lock.py::TestTicketLock::test_same_id_from_two_threads_serializes
  - tests/unit/test_process_lock.py::TestTicketLock::test_reentrant_same_id_in_same_thread_does_not_deadlock
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_lock_file_created_under_frob_dir
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_two_concurrent_allocations_get_distinct_ids
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_reentrant_in_same_thread_does_not_deadlock
- text: 'GIVEN a caller already holds `ticket_lock` for id X in the same thread

    WHEN it acquires `ticket_lock` for X again (reentrant call)

    THEN it does not deadlock (mirrors `derived_state_lock`''s reentrancy

    discipline, T-0933/T-0982 lineage).'
  evidence:
  - tests/unit/test_process_lock.py::TestTicketLock::test_lock_path_is_per_ticket_id
  - tests/unit/test_process_lock.py::TestTicketLock::test_two_different_ticket_ids_do_not_block_each_other
  - tests/unit/test_process_lock.py::TestTicketLock::test_same_id_from_two_threads_serializes
  - tests/unit/test_process_lock.py::TestTicketLock::test_reentrant_same_id_in_same_thread_does_not_deadlock
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_lock_file_created_under_frob_dir
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_two_concurrent_allocations_get_distinct_ids
  - tests/unit/test_process_lock.py::TestAllocatorLock::test_reentrant_in_same_thread_does_not_deadlock
threat: null
component: null
---
Ledger v2 design (docs/design/ledger-v2.md section 3) needs a per-ticket
file lock plus a single tiny allocator lock, replacing the one repo-wide
`ledger_lock` that serializes every ticket-mutating verb today regardless
of which ticket(s) they touch. Generalizes the T-0933/T-0982 fix (a
process-registry reentrancy bug caused by one shared contended resource)
by removing the shared resource for the common case (one verb, one
ticket).

Deliverables: a `ticket_lock(root, ticket_id)` context manager (per-ticket
flock, e.g. `tickets/T-####/.lock` or an flock on `ticket.md` itself) and
a separate `allocator_lock(root)` guarding only next-id computation. Both
must compose safely with the existing `ledger_lock` during the
compatibility window (section 7) -- do not remove `ledger_lock` yet, this
ticket only ADDS the new primitives alongside it.

GIVEN two callers each hold `ticket_lock` for different ticket ids
WHEN both proceed concurrently
THEN neither blocks the other (verified with a real concurrent-thread
test, not just code inspection).

GIVEN two callers both call the id allocator concurrently
WHEN both request a next id
THEN they receive distinct ids (interleaving regression test, mirroring
T-1090's `test_two_concurrent_finalize_draft_calls_get_distinct_ids`
shape).

GIVEN a caller already holds `ticket_lock` for id X in the same thread
WHEN it acquires `ticket_lock` for X again (reentrant call)
THEN it does not deadlock (mirrors `derived_state_lock`'s reentrancy
discipline, T-0933/T-0982 lineage).