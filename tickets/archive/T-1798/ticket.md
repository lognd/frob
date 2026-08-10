---
id: T-1798
title: 'post-land sweep regression from T-1534: 2 new error(s) (PRE001, SCOPE001)'
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
- tickets/T-1797/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1534 at commit 928170860b791b48dfcbda2902c2490bb10f795d found 2 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- PRE001  tickets/T-1797/ticket.md
- SCOPE001  tickets/T-1797/ticket.md

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-07: Spurious. Both findings (PRE001, SCOPE001) were against tickets/T-1797/ticket.md, a ledger file a land's sweep wrote to disk and never committed. Artifact of that file being untracked in root, not a defect in T-1534's change. Committed at c9dad538; a full unscoped check now reports neither rule. Second-order cost of the gap that DirtyMain-blocked lands four times today, now fixed by T-1758. (absorbed by T-1758)
