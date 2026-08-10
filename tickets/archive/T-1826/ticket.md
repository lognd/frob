---
id: T-1826
title: 'post-land sweep regression from T-1738: 4 new error(s) (ARCH001, ARCH103,
  COV001)'
state: dropped
kind: bug
origin: agent
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_query.py
- src/frob/tickets/_doable.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1738 at commit 0b51c676693c582db778cb8118061ed2af60065a found 4 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- ARCH001  src/frob/app/ticket_runner/_query.py
- ARCH001  src/frob/tickets/_doable.py
- ARCH103  src/frob/app/ticket_runner/_query.py
- COV001  src/frob/tickets/_doable.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-08: stale: findings already fixed by commit 411de3823 (docs(tickets): document frob ticket wave, fix its ARCH001/ARCH103 debris), landed after this sweep ticket was filed. Confirmed via unscoped frob check --json: no ARCH001/ARCH103/COV001 findings remain for src/frob/app/ticket_runner/_query.py or src/frob/tickets/_doable.py. T-1828 (duplicate) absorbed into this ticket, also dropped as stale.
