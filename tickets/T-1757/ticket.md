---
id: T-1757
title: 'post-land sweep regression from T-1754: 1 new error(s) (REL001)'
state: dropped
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1754 at commit 92a1dea0635fc5a4404a314db15bcb97255d35cf found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- REL001  pyproject.toml

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-07: verified stale against current main (2026-08-07): unscoped 'frob check --only release' shows 0 errors, 0 REL001 findings -- pyproject.toml/.frob-release.json both already agree at 0.367.0 (T-1627's land, which followed T-1754 and correctly recomputed the bump); the coordinator's by-hand REL001 fix already resolved the regression this sweep flagged