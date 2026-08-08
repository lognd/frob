---
id: T-1835
title: Collapse fortress/standard/rapid into one profile-depth dial on the land path
  (T-1686 epic finale)
state: dropped
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_profile.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1686's own stated payoff, not yet done: fortress=depth 0 (synchronous, refuse on red), standard=bounded depth K (quarantine+file on red), rapid=unbounded (never blocks, files and never reverts) should collapse into ONE mechanism parameterized by a profile-to-queue-depth dial, deleting the scattered 'if rapid:' seams in the land pipeline (confirmed still present: src/frob/app/ticket_runner/_land_cmd.py around line 2340-2342, rapid_land = effective is ProfileName.RAPID). The watermark/queue/worker/attribution/quarantine/crash-safety/enqueue-wiring mechanism this depends on is now COMPLETE (T-1687/T-1688/T-1690/T-1692/T-1693/T-1694/T-1736/T-1791, all landed) -- this ticket is purely the profile-dial collapse on top of that finished foundation. Filed as T-1686's own disclosed remainder rather than force it into T-1686's scope (which does not include _land_cmd.py).

## Drop reason
- 2026-08-08: exact duplicate of T-1696, which already exists as the T-1686 epic's own filed descendant for this exact profile-dial-collapse work (absorbed by T-1696)
