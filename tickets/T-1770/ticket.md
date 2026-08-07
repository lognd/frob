---
id: T-1770
title: 'post-land sweep regression from T-1767: 2 new error(s) (PRE001, SCOPE001)'
state: dropped
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1767 at commit 975ef58850a9f8f35a3b98af7da3e2cc43b7415b found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- PRE001  uv.lock
- SCOPE001  uv.lock

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-07: No longer reproducible. Main verified at 0 errors by a full unscoped 'frob check --json' at 09432c11; the rule this sweep flagged reports clean, fixed by a later land rather than by work on this ticket. PRE001 and SCOPE001 are clean; resolved by the T-1767 follow-up lands.
