---
id: T-2333
title: Persist frob worktree release-lease --force's reason on the ticket ledger,
  not just the WARNING log
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
