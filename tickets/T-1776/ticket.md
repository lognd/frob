---
id: T-1776
title: 'post-land sweep regression from T-1763: 1 new error(s) (REG002)'
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
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1763 at commit 25d6f3dc9036ddac407752ca7392e4d5ab11a3a5 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- REG002  docs/design/registry/check-coverage.yaml

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-07: No longer reproducible. Main verified at 0 errors by a full unscoped 'frob check --json' at 09432c11; the rule this sweep flagged reports clean, fixed by a later land rather than by work on this ticket. REG002 was the CHK-GATE-INV006 registry row that land's own Tier-A auto-fix re-filed on every attempt, reading the pre-land build's rule set. Root-caused and fixed there. (absorbed by T-1775)
