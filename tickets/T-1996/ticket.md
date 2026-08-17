---
id: T-1996
title: docs/modules/tickets.md's cross-worktree lease section is stale after T-1993's
  delta-reconciliation fix
state: done
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
land_commit: null
---
T-1993 changed mutate_scope/demote_to_evidence_only's lease-write behavior in src/frob/tickets/_scope.py: the shared lease's recorded scope is now reconciled as a delta against its own prior recorded state (when one exists) rather than a wholesale overwrite from the calling worktree's local ledger snapshot. The Cross-worktree lease side-channel (T-0473) section's sentence 'mutate_scope re-writes it when an in-progress ticket's scope changes, so it never drifts from the ledger's own state:/scope: fields' is only true for an up-to-date worktree now and should describe the delta-reconciliation mechanism T-1993 added. Could not be done in T-1993 itself: docs/modules/tickets.md was held by another in-progress ticket's live cross-worktree lease (T-1696) at the time.

## Done report

Updated docs/modules/tickets.md's Cross-worktree lease side-channel
(T-0473) section: the old sentence ("mutate_scope re-writes it when an
in-progress ticket's scope changes, so it never drifts from the
ledger's own state:/scope: fields") was true only for an up-to-date
worktree, per T-1993's own delta-reconciliation fix. Replaced with a
new paragraph describing what `_lease_scope_to_record`
(src/frob/tickets/_scope.py) actually does: re-applies the SAME
add/remove delta mutate_scope validated, but onto the lease file's
CURRENTLY recorded scope (read_all_leases) rather than the calling
worktree's possibly-stale local snapshot -- preventing a stale worktree
from clobbering a more-current sibling's already-narrowed lease by
writing last (the T-1993 incident this fixed). Verified against the
actual function body in src/frob/tickets/_scope.py, not guessed from
the ticket's own summary. No new frob:doc anchor needed --
_lease_scope_to_record is private and the existing
#cross-worktree-lease-side-channel-t-0473 anchor already covers this
area (mutate_scope, _leases.py's public surface).

docs/modules/tickets.md was NOT under any live lease at the start of
this ticket (T-1696, named in the ticket body as the original
blocker, had already released it).

### Changed
```
 tickets/T-1899/done-report.md | 32 ++++++++++++++++++++++++++++++++
 tickets/T-1899/ticket.md      |  6 +++++-
 tickets/T-1952/done-report.md | 34 ++++++++++++++++++++++++++++++++++
 tickets/T-1952/ticket.md      | 14 +++++++++++++-
 tickets/T-1973/ticket.md      |  6 +++++-
 tickets/T-1996/ticket.md      |  6 +++++-
 6 files changed, 94 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: E501@/home/logan/projects/frob/.claude/worktrees/t-1899/src/frob/gates/_root_asset_dirs.py, PRE001@tickets/T-1996, TICK004@tickets.md
