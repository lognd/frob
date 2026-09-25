---
id: T-draft-e388052a
title: 'ticket start/scope --after <sibling>: explicit override for same-series scope-lease
  overlap'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: high
parent: T-5630
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/_cli_parsers/_ticket/
- src/frob/tickets/_leases.py
- src/frob/tickets/_start.py
- tests/test_ticket_start_lease_overlap.py
- docs/modules/
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Friction measured three times on 2026-09-24/25: a successor ticket in the
same dispatch series (T-5161 after T-5403; T-5807 after T-draft-42b1e188;
the dry-run parity agent on _land_cmd.py) cannot `frob ticket start`
because its declared scope collides with the in-progress sibling's scope
lease. `ticket start --help` offers only --steal (stale worktree lease),
`ticket scope` has no override at all, and leases free only on land, so
the successor idles for the whole queue depth (hours) even though the
series order guarantees the sibling lands first.

Owner directive (systematize friction, one override flag; tiered safety):
this is a real decision, so it needs an explicit flag, not automatic
behaviour.

Deliver:
- `frob ticket start <id> --after <sibling-id>`: permit the scope-lease
  overlap with exactly that sibling, record the dependency as a
  blocked_by edge (so the successor cannot land before the sibling) and
  log the overlap in the lease file; refuse any overlap with a ticket
  other than the named sibling.
- `frob ticket scope --add ... --after <sibling-id>`: same semantics for
  a scope widened mid-work.
- Land-side: when the successor lands, its merge of dev already carries
  the sibling's hunks; the existing PassengerTickets/CrossTicketLeakage
  check must treat the named sibling as expected (the same posture as
  --allow-cross-ticket, but scoped to one id).
- Positive control: a test that plants two tickets with overlapping
  scope, shows plain `start` refuses with ScopeLeaseConflict, shows
  `--after` admits it and writes the blocked_by edge, and shows `--after`
  with a third ticket's id still refuses.
- Docs: the module doc that documents ScopeLeaseConflict gains the flag
  and its tier classification (explicit-flag tier).
