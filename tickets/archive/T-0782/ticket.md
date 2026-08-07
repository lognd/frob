---
id: T-0782
title: 'leases: implement T-0476 cleanup -- unlink stale leases opportunistically
  + TTL for dead-agent leases (daemon stops re-simulating)'
state: done
kind: bug
origin: auditor
created: '2026-07-23'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_leases.py
- src/frob/serve/_daemon.py
- tests/test_tickets_leases.py
- tests/test_serve_daemon.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_serve_daemon.py
  reason: 'Ticket''s own acceptance criteria requires a daemon-path regression test

    (TTL-expired lease skipped by poll_rebase_bot with exactly one log) --

    that test necessarily lives in tests/test_serve_daemon.py, the daemon''s

    existing test module, not tests/test_tickets_leases.py (which covers only

    frob.tickets._leases''s own primitives). Extending scope to cover it.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_tickets_leases.py::TestLeaseTtl::test_age_seconds_computes_elapsed_time
- tests/test_tickets_leases.py::TestLeaseTtl::test_age_seconds_none_for_unparseable_timestamp
- tests/test_tickets_leases.py::TestLeaseTtl::test_expired_past_ttl
- tests/test_tickets_leases.py::TestLeaseTtl::test_not_expired_within_ttl
- tests/test_tickets_leases.py::TestLeaseTtl::test_unparseable_timestamp_is_never_treated_as_expired
- tests/test_tickets_leases.py::TestOpportunisticUnlink::test_stale_path_lease_is_unlinked_from_disk
- tests/test_tickets_leases.py::TestOpportunisticUnlink::test_live_lease_is_never_unlinked
- tests/test_serve_daemon.py::TestPollRebaseBot::test_ttl_expired_lease_skipped_and_logged_once
- tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_ambiguous_stat_failure_does_not_unlink
- tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_ambiguous_failure_is_logged_once_per_process
- tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_genuine_enoent_still_unlinks
designated_repro_test: null
acceptance:
- text: GIVEN a lease whose worktree path no longer exists WHEN read_all_leases judges
    it stale THEN the file is unlinked (guarded so a live worktree lease is never
    removed) and the directory stops growing; GIVEN a live-path lease older than the
    TTL with no refresh THEN the daemon skips re-simulating it and logs once
  evidence:
  - tests/test_tickets_leases.py::TestOpportunisticUnlink::test_stale_path_lease_is_unlinked_from_disk
  - tests/test_tickets_leases.py::TestOpportunisticUnlink::test_live_lease_is_never_unlinked
  - tests/test_tickets_leases.py::TestAmbiguousLivenessGuard::test_ambiguous_stat_failure_does_not_unlink
  - tests/test_serve_daemon.py::TestPollRebaseBot::test_ttl_expired_lease_skipped_and_logged_once
threat: null
component: null
---
Audit M2: .git/frob-leases/ grows monotonically -- release only happens on clean IN_PROGRESS exit; stale leases are skipped-not-deleted (T-0476 deferral comment in read_all_leases); a dead agent with a still-existing worktree burns 2 git spawns per 20s daemon cycle forever. Implement the deferred T-0476 reconcile plus recorded_at TTL. Same files as T-0780 -- coordinator serializes dispatch.