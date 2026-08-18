---
id: T-2381
title: 'post-land sweep regression from T-2356: 27 new (rule, file) identit(ies),
  62 finding(s) (ARCH103, COV001, COV003, DOC001)'
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
- design
- docs/commands/release.md
- docs/design/gate-semantics-classification.md
- docs/guides/coordinator-scripts.md
- docs/modules/cli.md
- scripts/fleet_status.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/app/verify_runner.py
- src/frob/gates/_debt_deprecated.py
- src/frob/release/_cli.py
- src/frob/tickets/_land_git_ops.py
- src/frob/verify/_drain.py
- src/frob/verify/_quarantine.py
- src/frob/verify/_worker.py
- tests/test_release.py
- tickets.md
- tickets/T-1205
- tickets/T-1235
- tickets/T-1397
- tickets/T-1526
- tickets/T-1688
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2356 at commit e2ed60480f76189b19157b99c6357a8d563068e7 found 27 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (27), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 62 actual finding(s) across those 27 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH103  scripts/fleet_status.py
- ARCH103  src/frob/release/_cli.py
- COV001  scripts/fleet_status.py
- COV001  src/frob/tickets/_land_git_ops.py
- COV001  src/frob/verify/_drain.py
- COV001  src/frob/verify/_quarantine.py
- COV003  tickets/T-1205
- COV003  tickets/T-1235
- COV003  tickets/T-1397
- COV003  tickets/T-1526
- COV003  tickets/T-1688
- DOC001  docs/commands/release.md
- DOC002  scripts/fleet_status.py
- DOC002  src/frob/app/verify_runner.py
- DOC002  src/frob/verify/_drain.py
- DOC011  docs/design/gate-semantics-classification.md
- DOC011  docs/guides/coordinator-scripts.md
- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py
- E501  /home/logan/projects/frob/src/frob/verify/_worker.py
- PERF003  src/frob/gates/_debt_deprecated.py
- PERF004  src/frob/app/ticket_runner/_new.py
- RENDER001  src/frob/release/_cli.py
- SEC110  tests/test_release.py
- SELFAUDIT001  design
- TICK003  tickets.md
- TICK004  tickets.md
- WIRE003  docs/modules/cli.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- ARCH103  src/frob/release/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/tickets/_land_git_ops.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/verify/_drain.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/verify/_quarantine.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1205  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1235  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1397  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1526  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1688  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC001  docs/commands/release.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/app/verify_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/verify/_drain.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/design/gate-semantics-classification.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/guides/coordinator-scripts.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/app/ticket_runner/_rapid_sweep.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/verify/_worker.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/gates/_debt_deprecated.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- RENDER001  src/frob/release/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  tests/test_release.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK003  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE003  docs/modules/cli.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.