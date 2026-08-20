---
id: T-2689
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
- 2026-08-19: Measured (T-2690 series triage): cites T-draft-be1e79b5, which git history confirms was renamed (git show -M --name-status a44f96e60: R099 tickets/T-draft-be1e79b5/ticket.md -> tickets/T-2678/ticket.md) to the real, live ticket T-2678 ('frob ticket body writes an archived ticket's update to a fresh non-archive...', state=queued) -- the exact underlying tool bug T-2689's own quoted excerpt (T-2685's Done report, 'Filed T-draft-be1e79b5 for the underlying tool bug') describes. A bookkeeping duplicate, not independent work. Root mechanism (the auto-recovery mechanism that filed T-2689 without checking git rename history first) fixed in T-2690.
