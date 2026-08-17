---
id: T-2035
title: Recovered from T-2036's phantom TICK006 citation of T-2030
state: dropped
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2036's Done report claimed T-2030 was filed, but T-2030 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> rom
the root checkout directly; the two F401 findings it named are
confirmed still live.

NOT fixed here (explicitly out of scope, filed separately): T-2030,
the sweep writing into a concurrent agent's own worktree -- a
root-path-resolution defect the coordinator suspects shares an
upstream cause wi

## Drop reason
- 2026-08-10: Re-measured: T-2030 exists in tickets.md with state=done, full evidence and Done report -- not a phantom citation. The TICK006 finding is stale; nothing left to implement.
