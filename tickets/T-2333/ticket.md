---
id: T-2333
title: Persist frob worktree release-lease --force's reason on the ticket ledger,
  not just the WARNING log
state: done
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
- src/frob/app/worktree_runner.py
- docs/modules/tickets-lifecycle.md
- src/frob/tickets/_leases.py
- tests/test_ticket_leases_cross_worktree.py
evidence_scope:
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: probe scope/lease status
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: 'T-2333: force_release_lease (src/frob/tickets/_leases.py) is where the
    operator-supplied --force reason is threaded through and needs to write the new
    ledger-persisted audit entry alongside its existing WARNING log'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_ticket_leases_cross_worktree.py
  reason: 'T-2333: added a positive-control test proving the new lease_force_releases
    ledger persistence'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_ticket_leases_cross_worktree.py::TestForceReleaseLease::test_reason_is_persisted_to_the_ticket_ledger
- tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli::test_release_lease_cli_force_releases_a_live_looking_lease
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`frob worktree release-lease --force --reason TEXT` (T-1777) folds the
operator's reason into `force_release_lease`'s own WARNING log line, not
a persisted ticket-ledger field -- the log line IS the audit trail today.
T-1777's own design intent was closer to `frob ticket scope --reason`
(a `scope_changes`-shaped, ledger-persisted, `frob ticket show`-visible
audit entry), but `src/frob/tickets/_models.py` was under T-2302's live
cross-worktree lease for T-1777's entire duration and could not be added
to scope.

Add a `lease_force_releases` (or similar) append-only audit list to the
`Ticket` model, mirroring `ScopeChangeEntry`'s shape (op/reason/actor/at,
here also the pre-release `lease_staleness_reason` outcome if any), and
have `frob worktree release-lease --force` write an entry there in
addition to the existing WARNING log -- so a forced release is visible
in `frob ticket show <id>` the same way a scope change already is, not
only in process logs.