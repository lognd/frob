---
id: T-4685
title: 'release_lease: surface a real unlink failure as Err, not just an ERROR log'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: medium
parent: null
tier: ticket
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_leases.py
- tests/test_ticket_leases.py
- src/frob/tickets/_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4659 hardened `release_lease`'s ERROR-level logging on a real unlink
failure but could not change its Result contract to `Err` in the same
change: the one existing test pinning that contract,
`tests/test_ticket_leases.py::TestRecordReleaseRenameLeaseErrorBranches.test_release_lease_degrades_on_unlink_failure`,
sits under a live T-4625 lease on `tests/test_ticket_leases.py` and could
not be extended without a scope conflict (measured 2026-09-19: `frob
ticket scope T-4659 --add tests/test_ticket_leases.py` refused with
ScopeLeaseConflict against T-4625).

Once T-4625 releases that file: change `release_lease` (src/frob/tickets/_leases.py)
to return `Err(LeaseError.ReleaseFailed)` on a genuine unlink OSError
(add the ReleaseFailed variant back to LeaseError), update
test_release_lease_degrades_on_unlink_failure to assert `result.is_err`
and the returned error kind, and thread that Err through
`frob.tickets._evidence._sync_cross_worktree_lease`'s callers so a
terminal transition that cannot release its lease surfaces a hard error
rather than only an ERROR log line -- the original T-4659 plan's
"surfaces a Result error" acceptance point, deferred here.

scope: src/frob/tickets/_leases.py, tests/test_ticket_leases.py,
src/frob/tickets/_evidence.py
blocked_by: T-4625
