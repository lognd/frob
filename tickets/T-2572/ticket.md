---
id: T-2572
title: 'post-land sweep regression from T-2534: 27 new (rule, file) identit(ies),
  36 finding(s) (COV001, COV003, COV004, DOC001)'
state: dropped
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/commands/release.md
- docs/design/gate-semantics-classification.md
- docs/modules/cli.md
- docs/modules/gates.md
- src/frob/app/fmt_runner.py
- src/frob/app/ticket_runner/_ledger_mirror.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/gates/_refs_schema.py
- src/frob/lang/_support.py
- src/frob/release/_cli.py
- src/frob/scaffold/project.py
- src/frob/strata/_multifile.py
- tickets.md
- tickets/T-1397
- tickets/T-1526
- tickets/T-1688
- tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- tickets/T-2344
- tickets/T-2348
- tickets/T-2365
- tickets/T-2561/ticket.md
- tickets/T-2570/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2534 at commit fd18698e0bac5c1ab181bc946a45ef08b9f39a45 found 27 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (27), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 36 actual finding(s) across those 27 identit(ies).

New (rule, file) identit(ies) filed here:

- COV001  src/frob/app/fmt_runner.py
- COV001  src/frob/gates/_refs_schema.py
- COV001  src/frob/strata/_multifile.py
- COV003  tickets/T-1397
- COV003  tickets/T-1526
- COV003  tickets/T-1688
- COV003  tickets/T-2344
- COV003  tickets/T-2348
- COV003  tickets/T-2365
- COV004  tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- COV004  tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- DOC001  docs/commands/release.md
- DOC002  src/frob/gates/_refs_schema.py
- DOC005  docs/modules/cli.md
- DOC006  tickets/T-2561/ticket.md
- DOC006  tickets/T-2570/ticket.md
- DOC008  docs/modules/gates.md
- DOC011  docs/design/gate-semantics-classification.md
- DOCENUM001  docs/modules/gates.md
- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_ledger_mirror.py
- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_verify.py
- E501  /home/logan/projects/frob/src/frob/scaffold/project.py
- LANG004  src/frob/lang/_support.py
- RENDER001  src/frob/release/_cli.py
- TEST001  src/frob/strata/_multifile.py
- TICK003  tickets.md
- TICK004  tickets.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  src/frob/app/fmt_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/gates/_refs_schema.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/strata/_multifile.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1397  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1526  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1688  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-2344  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-2348  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-2365  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV004  tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC001  docs/commands/release.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/gates/_refs_schema.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC005  docs/modules/cli.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  tickets/T-2561/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC006  tickets/T-2570/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC008  docs/modules/gates.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/design/gate-semantics-classification.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOCENUM001  docs/modules/gates.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_ledger_mirror.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_verify.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/scaffold/project.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG004  src/frob/lang/_support.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- RENDER001  src/frob/release/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TEST001  src/frob/strata/_multifile.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK003  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-18: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (COV001 src/frob/app/fmt_runner.py, COV001 src/frob/gates/_refs_schema.py, COV001 src/frob/strata/_multifile.py, COV003 tickets/T-1397, COV003 tickets/T-1526, COV003 tickets/T-1688, COV003 tickets/T-2344, COV003 tickets/T-2348, COV003 tickets/T-2365, COV004 tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004 tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001 docs/commands/release.md, DOC002 src/frob/gates/_refs_schema.py, DOC005 docs/modules/cli.md, DOC006 tickets/T-2561/ticket.md, DOC006 tickets/T-2570/ticket.md, DOC008 docs/modules/gates.md, DOC011 docs/design/gate-semantics-classification.md, DOCENUM001 docs/modules/gates.md, E501 src/frob/app/ticket_runner/_ledger_mirror.py, E501 src/frob/app/ticket_runner/_verify.py, E501 src/frob/scaffold/project.py, LANG004 src/frob/lang/_support.py, RENDER001 src/frob/release/_cli.py, TEST001 src/frob/strata/_multifile.py, TICK003 tickets.md, TICK004 tickets.md) is absent from a full unscoped `frob check --json` run that completed with no budget deferral and no failed/silent tool stage at T-2100's deferred sweep (T-2521: this drop only fires when that measurement itself completed -- no budget deferral, no failed/silent tool stage -- never on an unmeasured or partial run), i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
