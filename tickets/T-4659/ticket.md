---
id: T-4659
title: 'Lease lifecycle: release on every terminal transition; drop no longer leaves
  .git/frob-leases/<id>.json'
state: in-progress
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4653
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- tests/unit/test_lease_lifecycle.py
- docs/modules/tickets-lifecycle.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
evidence:
- tests/unit/test_lease_lifecycle.py::TestReleaseLeaseLifecycle::test_drop_releases_lease
- tests/unit/test_lease_lifecycle.py::TestReleaseLeaseLifecycle::test_fail_releases_lease
- tests/unit/test_lease_lifecycle.py::TestReleaseLeaseLifecycle::test_requeue_releases_lease
- tests/unit/test_lease_lifecycle.py::TestReleaseLeaseHardening::test_missing_lease_is_a_silent_ok
- tests/unit/test_lease_lifecycle.py::TestReleaseLeaseHardening::test_real_unlink_failure_logs_at_error
- tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_release_lease_degrades_on_unlink_failure
designated_repro_test: null
acceptance:
- text: Given an in-progress ticket holding a lease, when `frob ticket drop` runs,
    then .git/frob-leases/<id>.json is removed and a sibling `scope --add` on the
    same path succeeds.
  evidence:
  - tests/unit/test_lease_lifecycle.py::TestReleaseLeaseLifecycle::test_drop_releases_lease
  - tests/unit/test_lease_lifecycle.py::TestReleaseLeaseLifecycle::test_fail_releases_lease
  - tests/unit/test_lease_lifecycle.py::TestReleaseLeaseLifecycle::test_requeue_releases_lease
  - tests/unit/test_lease_lifecycle.py::TestReleaseLeaseHardening::test_missing_lease_is_a_silent_ok
  - tests/unit/test_lease_lifecycle.py::TestReleaseLeaseHardening::test_real_unlink_failure_logs_at_error
  - tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches::test_release_lease_degrades_on_unlink_failure
- text: 'POSITIVE CONTROL: tests/unit/test_lease_lifecycle.py::test_drop_releases_lease
    starts a ticket, drops it, and asserts the lease file is gone. It FAILS on dev
    today (the file survives; measured 2026-09-19) and passes after this leaf.'
  evidence: []
- text: 'Given the same, for `fail` and `requeue`: tests/unit/test_lease_lifecycle.py::test_fail_releases_lease
    and ::test_requeue_releases_lease each hold.'
  evidence: []
- text: docs/modules/tickets-lifecycle.md states the acquire/release table (transition
    -> lease effect) and is updated in this same change.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Kernel decoupling leaf (LEASE story). ~2 points.

Measured 2026-09-19 (T-draft-15749ed2): `frob ticket drop` leaves .git/frob-leases/<id>.json in place. A dropped ticket therefore keeps blocking every sibling `scope --add` with ScopeLeaseConflict and every PassengerTickets selection, until a human deletes the file by hand. The root cause is that the lease has no lifecycle at all (T-3927): it is created as a side effect and never owned.

Give the lease an explicit lifecycle in src/frob/tickets/_leases.py:
  ACQUIRE on `start`
  RELEASE on EVERY terminal transition: close, drop, fail, requeue
Each transition logs id, path set, and acquire/release outcome. A terminal transition that cannot release logs at ERROR and surfaces a Result error rather than silently leaving the file.
