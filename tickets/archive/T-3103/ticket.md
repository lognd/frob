---
id: T-3103
title: Recovered from T-3095's phantom TICK006 citation of T-3106
state: dropped
kind: bug
origin: agent
created: '2026-08-27'
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-3095's Done report claimed T-3106 was filed, but T-3106 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> correct, and the concurrent-poll acceptance
  criterion (clean root at every sample UNTIL publish) says nothing
  about what happens after. Filed as T-3106.
- Pre-commit sweep: NOT addressed here -- correctly the hard one (Tier-A
  auto-fix mutates content, so its output must land in the composed

## Drop reason
- 2026-08-27: False positive of the TICK006 auto-recovery (T-1544): it judged T-3095's citation of T-3106 phantom because T-3106 had not yet landed from its sibling worktree at snapshot time. T-3106 now exists and is queued ('Fix fleet_status.py orphan false-positive and add frob process reap command'), so this recovery ticket is a pure duplicate of it. Underlying race filed separately.
