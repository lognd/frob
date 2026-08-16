---
id: T-2168
title: 'post-land sweep regression from T-2108, T-2129: 2 new (rule, file) identit(ies),
  4 finding(s) (ARCH001, DRIFT001)'
state: dropped
kind: bug
origin: agent
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2108, T-2129 at commit 90ecdd92c3d14a056d325b2da87db4941ec6045a found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 4 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH001  src/frob/app/ticket_runner/_land_cmd.py
- DRIFT001  src/frob/app/ticket_runner/_land_cmd.py

T-2009: 2 lands (T-2108, T-2129) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-2108, T-2129 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (4 batch commits' touched symbols all reach this finding); candidate commits: ['5da87ec3f37553aac0c9b552e64efdcfa2805650', '183f59675edbd7d4e1be8137dadacc140cd7493e', 'f32fa5f215b068b0751204bd39340e3e708f3e21', 'f0ab85d0ee84cefe83d163431e6574a4739d1a14']
- DRIFT001  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (4 batch commits' touched symbols all reach this finding); candidate commits: ['5da87ec3f37553aac0c9b552e64efdcfa2805650', '183f59675edbd7d4e1be8137dadacc140cd7493e', 'f32fa5f215b068b0751204bd39340e3e708f3e21', 'f0ab85d0ee84cefe83d163431e6574a4739d1a14']

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-16: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (ARCH001 src/frob/app/ticket_runner/_land_cmd.py, DRIFT001 src/frob/app/ticket_runner/_land_cmd.py) is absent from the fresh unscoped measurement at T-2181's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
