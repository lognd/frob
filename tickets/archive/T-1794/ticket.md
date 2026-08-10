---
id: T-1794
title: 'post-land sweep regression from T-1620: 2 new error(s) (PRE001, SCOPE001)'
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
- tickets/T-1792/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1620 at commit 10edb1f48c717133affac06e85ee8936db455411 found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- PRE001  tickets/T-1792/ticket.md
- SCOPE001  tickets/T-1792/ticket.md

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-07: Spurious: an artifact of how the deferred sweep invokes frob check, not a defect in the ticket it names. The sweep runs UNSCOPED, so PRE001/SCOPE001 fire with 'diff touches N file(s) but no active ticket is derivable' -- a condition an unscoped run guarantees by construction. Reproduced directly: a bare 'frob check' on clean main emits exactly these two and nothing else. Systemic, not per-ticket; the sweep must pass --ticket or exclude the two rules that require one.
