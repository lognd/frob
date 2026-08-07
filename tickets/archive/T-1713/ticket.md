---
id: T-1713
title: 'post-land sweep regression from T-1679: 1 new error(s) (COV003)'
state: dropped
kind: bug
origin: agent
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tickets/T-1637
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1679 at commit 4d04697acd542805fab4bc3b41ffda11823a3db7 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs:

- COV003  tickets/T-1637

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-06: auto-filed by the T-1684 deferred sweep for the same COV003 (T-1637's evidence broken by T-1679's test rename); T-1714 is a superset -- it covers that COV003 plus the 2 ty invalid-parameter-default errors from the same land series, and carries the analysis of why both safety nets missed them (absorbed by T-1714)