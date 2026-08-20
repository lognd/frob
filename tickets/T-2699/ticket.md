---
id: T-2699
title: Recovered from T-2685's phantom TICK006 citation of T-draft-be1e79b5
state: dropped
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2685's Done report claimed T-draft-be1e79b5 was filed, but T-draft-be1e79b5 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> n afterward; confirmed no other id is duplicated across
`tickets/` and `tickets/archive/` repo-wide (`comm -12` on the sorted
id lists, empty). Filed T-draft-be1e79b5 for the underlying tool bug
(coordinator does not need to take it).

### Verification

Before: `frob check --only docanchor --only dr

## Drop reason
- 2026-08-20: phantom citation T-draft-be1e79b5 resolves via git rename to T-2678 (git show -M --name-status a44f96e60: R099 tickets/T-draft-be1e79b5/ticket.md -> tickets/T-2678/ticket.md); this recovery ticket is itself a duplicate filing caused by the T-2699/T-2701 bug fixed in T-2702 -- re-measured 2026-08-20 via _resolve_via_git_rename_measured(root, 'T-draft-be1e79b5') = ('T-2678', True)
