---
id: T-1765
title: 'post-land sweep regression from T-1760: 1 new error(s) (REL001)'
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
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1760 at commit 4d23838e4dde96f85f9205952a8638e73b9688f3 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- REL001  pyproject.toml

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-07: No longer reproducible. Main verified at 0 errors by a full unscoped 'frob check --json' at 09432c11; the rule this sweep flagged reports clean, fixed by a later land rather than by work on this ticket. REL001 (release bump) is clean.
