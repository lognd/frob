---
id: T-2212
title: 'post-land sweep regression from T-2196, T-2201: 2 new (rule, file) identit(ies),
  2 finding(s) (ARCH001, COV001)'
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
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2196, T-2201 at commit 81aba19db295e0fd6d231e11390607e6294fa7a5 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 2 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH001  scripts/fleet_status.py
- COV001  scripts/fleet_status.py

T-2009: 2 lands (T-2196, T-2201) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-2196, T-2201 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  scripts/fleet_status.py  -> UNATTRIBUTED (6 batch commits' touched symbols all reach this finding); candidate commits: ['f2ec5e4584336620940d035848c7e98112b9d952', '97fbf751deca456af7ce5557da8ee36cd1b94814', '630b6f866461390a15e5e085d6fb0daa6120ee16', 'd63371c86d734e51f3043c56cff473aba98b0aec', '79c0250d279166239b6b3a5fa05975b669291c3e', '0ab334af19d641a5f5356d778d060b7419bc07f8']
- COV001  scripts/fleet_status.py  -> UNATTRIBUTED (6 batch commits' touched symbols all reach this finding); candidate commits: ['f2ec5e4584336620940d035848c7e98112b9d952', '97fbf751deca456af7ce5557da8ee36cd1b94814', '630b6f866461390a15e5e085d6fb0daa6120ee16', 'd63371c86d734e51f3043c56cff473aba98b0aec', '79c0250d279166239b6b3a5fa05975b669291c3e', '0ab334af19d641a5f5356d778d060b7419bc07f8']

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-16: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (ARCH001 scripts/fleet_status.py, COV001 scripts/fleet_status.py) is absent from the fresh unscoped measurement at T-2207's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
