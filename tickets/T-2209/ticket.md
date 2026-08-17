---
id: T-2209
title: 'post-land sweep regression from T-2199: 2 new (rule, file) identit(ies), 4
  finding(s) (, E501)'
state: dropped
kind: bug
origin: agent
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- /home/logan/projects/frob/src/frob/lang/_nodes.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2199 at commit c59592f0a23f9a53620e6440a8ae5c0feccead73 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 4 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

-   
- E501  /home/logan/projects/frob/src/frob/lang/_nodes.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

-     -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/lang/_nodes.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-16: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named ( ., E501 /home/logan/projects/frob/src/frob/lang/_nodes.py) is absent from the fresh unscoped measurement at doable's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
