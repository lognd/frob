---
id: T-2260
title: 'post-land sweep regression from T-2243, T-2233, T-2241, T-2248: 7 new (rule,
  file) identit(ies), 8 finding(s) (CLAUDE001, DRIFT001, E501, F541)'
state: queued
kind: bug
origin: agent
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/sync-claude-config.py
- design
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/lang/_nodes.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2243, T-2233, T-2241, T-2248 at commit fdc105876fa83d310effe9170e79b3b1200c4271 found 7 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (7), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 8 actual finding(s) across those 7 identit(ies).

New (rule, file) identit(ies) filed here:

- CLAUDE001  .claude/hooks/sync-claude-config.py
- DRIFT001  src/frob/app/ticket_runner/_land_cmd.py
- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py
- DRIFT001  src/frob/lang/_nodes.py
- E501  src/frob/lang/_nodes.py
- F541  tests/test_ticket_work_and_land_finish.py
- SELFAUDIT001  design

T-2009: 4 lands (T-2243, T-2233, T-2241, T-2248) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-2243, T-2233, T-2241, T-2248 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- CLAUDE001  .claude/hooks/sync-claude-config.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/app/ticket_runner/_land_cmd.py  -> UNATTRIBUTED (8 batch commits' touched symbols all reach this finding); candidate commits: ['beb1d2def761d8ddbf82d965213bea3a5cab3ffe', 'a1d37e461d4818c14af3a4a00170d60b083955ac', '5caf24a262a336d6deef5b7a61749e1a2149cc79', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '1fbcfe328fd36724fe1350a58d6122828c5b8fdc', '8ea951cb7ce8d2578704c9c3c6cd78159851588f', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f']
- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py  -> attributed to T-2208 (commit 9b53f81e11e4, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_rapid_sweep.py::_auto_dispose_filed_findings
- DRIFT001  src/frob/lang/_nodes.py  -> attributed to T-2195 (commit 808e0c6fb3f4, already closed/dropped -- filed below) via src/frob/lang/_nodes.py::_declared_python_source_roots
- E501  src/frob/lang/_nodes.py  -> attributed to T-2195 (commit 808e0c6fb3f4, already closed/dropped -- filed below) via src/frob/lang/_nodes.py::_declared_python_source_roots
- F541  tests/test_ticket_work_and_land_finish.py  -> UNATTRIBUTED (4 batch commits' touched symbols all reach this finding); candidate commits: ['a1d37e461d4818c14af3a4a00170d60b083955ac', '0f2271017a3734245ce7ac2ba5deb5bcefaa2429', '150ba1ccd26ceafef7fdbe678203300b48176979', '2d341516c3bb7e9829e88856d5dd4745748fd04f']
- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.