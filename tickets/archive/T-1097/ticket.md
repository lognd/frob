---
id: T-1097
title: 'daemon: resource leases/semaphores (coverage=1 writer) arbitrated by the socket
  daemon'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
blocked_by:
- T-1092
- T-1095
parent: T-0321
tier: story
sprint: null
scope:
- src/frob/serve/**
- src/frob/testing/**
- docs/modules/serve.md
- docs/modules/testing.md
- tickets.md
- tests/test_serve_leases.py
- tests/test_app_daemon_proxy.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_app_daemon_proxy.py
  reason: 'tests/test_serve_leases.py imports _start_daemon from this file (DUP001:
    reuse the existing helper rather than a byte-identical duplicate)'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_serve_leases.py::TestResourceLeaseManager::test_second_acquire_blocks_until_first_releases
- tests/test_serve_leases.py::TestResourceLeaseManager::test_acquire_times_out_if_never_freed
- tests/test_serve_leases.py::TestResourceLeaseManager::test_release_holder_frees_every_resource_that_holder_held
- tests/test_serve_leases.py::TestResourceLeaseManager::test_distinct_resources_do_not_contend
- tests/test_serve_leases.py::TestResourceLeaseManager::test_reentrant_acquire_by_same_holder_does_not_deadlock
- tests/test_serve_leases.py::TestResourceLeaseManager::test_release_of_unheld_resource_is_a_noop
- tests/test_serve_leases.py::TestLeaseRpc::test_explicit_release_frees_the_slot_for_the_next_waiter
- tests/test_serve_leases.py::TestLeaseRpc::test_second_client_blocks_until_first_releases
- tests/test_serve_leases.py::TestConnectionCrashReleasesLease::test_closing_connection_without_explicit_release_frees_the_lease
designated_repro_test: null
acceptance:
- text: GIVEN N concurrent clients requesting a coverage run WHEN the daemon arbitrates
    access THEN exactly one holds the coverage writer semaphore at a time and the
    rest block or receive the shared result, with no two coverage subprocesses running
    concurrently against overlapping state
  evidence:
  - tests/test_serve_leases.py::TestLeaseRpc::test_second_client_blocks_until_first_releases
- text: GIVEN a client holding a lease crashes or disconnects WHEN the daemon detects
    the dead connection THEN the lease is released automatically (no permanently stuck
    semaphore requiring a daemon restart)
  evidence:
  - tests/test_serve_leases.py::TestConnectionCrashReleasesLease::test_closing_connection_without_explicit_release_frees_the_lease
threat: null
component: null
---
Child (f) of T-0321. Today T-0322's coverage.lock is a plain per-worktree fcntl.flock with no arbitration beyond OS-level blocking, no visibility into who holds it, and no daemon-mediated release-on-crash semantics. Once T-1095 makes coverage single-flight CROSS-worktree (arbitrated by the T-1092 daemon rather than a per-worktree file lock), formalize it as a general named-resource lease/semaphore primitive the daemon owns (starting with coverage=1 writer, per T-0321's body), so other future contended resources (e.g. a future write-serializing need) can register the same way instead of each inventing its own flock convention. Lease release must be tied to socket connection liveness (a crashed/killed client's lease is freed by the daemon detecting the closed connection), not just an explicit release call, to satisfy T-0321's requirement 3 (killing a client loses nothing, nothing to clean up).