---
id: T-2297
title: 'post-land sweep regression from T-1783: 6 new (rule, file) identit(ies), 15
  finding(s) (, E402, E501, F541)'
state: queued
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- /home/logan/projects/frob/scripts/fleet_status.py
- /home/logan/projects/frob/src/frob/lang/_nodes.py
- /home/logan/projects/frob/tests/test_ticket_work_and_land_finish.py
- /home/logan/projects/frob/tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: /home/logan/projects/frob/tests/test_ticket_land.py
  reason: F841 unused variable in test_ticket_land.py reproduces on re-measure; keeping
    it in scope actually -- retracting this remove
  actor: logan
  at: '2026-08-17'
- op: add
  glob: /home/logan/projects/frob/tests/test_ticket_land.py
  reason: 'correcting accidental removal: F841 tests/test_ticket_land.py is a genuine,
    currently-reproducing finding, re-adding'
  actor: logan
  at: '2026-08-17'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-1783 at commit 153f84bbaddd32ed6f521deecad6f3d154e8746c found 6 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (6), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 15 actual finding(s) across those 6 identit(ies).

New (rule, file) identit(ies) filed here:

-   
- E402  /home/logan/projects/frob/scripts/fleet_status.py
- E501  /home/logan/projects/frob/scripts/fleet_status.py
- E501  /home/logan/projects/frob/src/frob/lang/_nodes.py
- F541  /home/logan/projects/frob/tests/test_ticket_work_and_land_finish.py
- F841  /home/logan/projects/frob/tests/test_ticket_land.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

-     -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E402  /home/logan/projects/frob/scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/lang/_nodes.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F541  /home/logan/projects/frob/tests/test_ticket_work_and_land_finish.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F841  /home/logan/projects/frob/tests/test_ticket_land.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.