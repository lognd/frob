---
id: T-1973
title: Add T-1946/T-1944 doc sections to docs/modules/tickets.md once T-1967's lease
  frees
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
Both T-1946 (orphaned-evidence-deletion land guard) and T-1944
(evidence-only scope) wrote doc sections for docs/modules/tickets.md
during implementation, but could not commit them: T-1967 (in-progress,
another agent) holds a live cross-worktree lease on this exact file, so
`frob ticket scope --add docs/modules/tickets.md` refuses with
ScopeLeaseConflict for both tickets.

The doc prose for both sections is recoverable from this ticket's own
worktree history (detector-fp) if still present, or can be re-authored
fresh from each ticket's own Done report -- neither is large. Add:
- "## Orphaned evidence deletion (T-1946)" (documenting `_check_
  orphaned_evidence_deletion` in src/frob/tickets/_land.py)
- "## Evidence-only scope (T-1944)" (documenting `Ticket.evidence_scope`
  and `demote_to_evidence_only` in src/frob/tickets/_models.py and
  _scope.py)

Once T-1967 lands/closes and releases the lease.
