---
id: T-1996
title: docs/modules/tickets.md's cross-worktree lease section is stale after T-1993's
  delta-reconciliation fix
state: in-progress
kind: docs
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/modules/tickets.md
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1993 changed mutate_scope/demote_to_evidence_only's lease-write behavior in src/frob/tickets/_scope.py: the shared lease's recorded scope is now reconciled as a delta against its own prior recorded state (when one exists) rather than a wholesale overwrite from the calling worktree's local ledger snapshot. The Cross-worktree lease side-channel (T-0473) section's sentence 'mutate_scope re-writes it when an in-progress ticket's scope changes, so it never drifts from the ledger's own state:/scope: fields' is only true for an up-to-date worktree now and should describe the delta-reconciliation mechanism T-1993 added. Could not be done in T-1993 itself: docs/modules/tickets.md was held by another in-progress ticket's live cross-worktree lease (T-1696) at the time.