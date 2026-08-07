---
id: T-1722
title: 'post-land sweep regression from T-1706: 1 new error(s) (ARCH103)'
state: dropped
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- .claude/hooks/sync-claude-config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1706 at commit c3277f2b57124045e489e06356322d21dbc951b0 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs:

- ARCH103  .claude/hooks/sync-claude-config.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-07: ARCH103 in .claude/hooks/sync-claude-config.py not present on current main: frob check --only archgate shows 0 findings for that file, only the 4 pre-existing _coverage_refresh.py errors (T-1723's target) remain; already fixed/absorbed elsewhere or was a stale baseline entry