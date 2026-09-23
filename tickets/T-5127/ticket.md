---
id: T-5127
title: Recovered from T-4546's phantom TICK006 citation of T-4939
state: queued
kind: bug
origin: agent
created: '2026-09-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-4546's Done report claimed T-4939 was filed, but T-4939 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> x, checked
   from ROOT).
6. kind=ux, not bug -- BUG002 repro-designation N/A.
7. tickets/T-4546/ticket.md's `id:` == T-4546; no stray draft dirs
   (T-4939 below is a genuinely new draft, not a promotion).
8. Evidence bound AFTER the last code commit (d72d04800) -- the only
   commit after evidence