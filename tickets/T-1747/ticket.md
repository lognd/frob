---
id: T-1747
title: 'post-land sweep regression from T-1715: 1 new error(s) (TICK003)'
state: dropped
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1715 at commit 7ca65c2586b05b508800541746413944e8f291bf found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs:

- TICK003  tickets.md

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-07: verified stale against current main (2026-08-07): unscoped 'frob check --only tickets' shows 0 errors, 0 TICK003 findings -- the coordinator's own by-hand REL001/TICK003 fixes after this ticket was auto-filed already resolved the tickets.md issue this sweep flagged