---
id: T-2399
title: Recovered from T-2386's phantom TICK006 citation of T-2388
state: dropped
kind: bug
origin: agent
created: '2026-08-18'
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
Auto-filed by the TICK006 Tier-A fix (T-1544): T-2386's Done report claimed T-2388 was filed, but T-2388 resolves to no block in tickets.md or tickets-archive.md -- a phantom filing trail. The original claim's own surrounding text (the only surviving description of the intended work) is quoted verbatim below; review and refine as needed.

> manifest
shape.

All tests use tmp_path --claude-dir, never the real ~/.claude, per the
ticket's own instruction.

Filed as part of T-2384's series: T-2388 (PORT001 meta-gate, coordinator
directive) and T-2389 (source-root retarget group 1) queued as siblings, not
completed in this ticket.

### Cha

## Drop reason
- 2026-08-18: false positive: T-2388 genuinely exists (tickets/T-2388/ticket.md, filed on main before T-2386 started) -- the TICK006 Tier-A auto-fix misread a citation in T-2386's Done report as a phantom filing
