---
id: T-2545
title: 'post-land sweep regression from T-2527: 37 new (rule, file) identit(ies),
  62 finding(s) (ARCH103, COV001, COV003, DOC001)'
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
- design
- docs/commands/release.md
- docs/design/gate-semantics-classification.md
- docs/modules/cli.md
- docs/modules/gates.md
- src/frob/app/fmt_runner.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/verify_runner.py
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_refs_schema.py
- src/frob/lang/_support.py
- src/frob/release/_cli.py
- src/frob/scaffold/_skills_sync.py
- src/frob/strata/_multifile.py
- src/frob/testing/_collect_kotlin.py
- src/frob/vet/_capability_core.py
- tests/test_capability_registry.py
- tests/test_release.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_main_entry.py
- tickets.md
- tickets/T-1205
- tickets/T-1235
- tickets/T-1397
- tickets/T-1526
- tickets/T-1688
- tickets/T-2344
- tickets/T-2348
- tickets/T-2365
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
The deferred post-land unscoped sweep (T-1684) for T-2527 at commit 2694ad3e6762c76c997d57beb7d38b8178f737a1 found 37 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (37), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 62 actual finding(s) across those 37 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH103  src/frob/release/_cli.py
- COV001  src/frob/app/fmt_runner.py
- COV001  src/frob/gates/_refs_schema.py
- COV001  src/frob/strata/_multifile.py
- COV003  tickets/T-1205
- COV003  tickets/T-1235
- COV003  tickets/T-1397
- COV003  tickets/T-1526
- COV003  tickets/T-1688
- COV003  tickets/T-2344
- COV003  tickets/T-2348
- COV003  tickets/T-2365
- DOC001  docs/commands/release.md
- DOC002  src/frob/gates/_refs_schema.py
- DOC005  docs/modules/cli.md
- DOC008  docs/modules/gates.md
- DOC011  docs/design/gate-semantics-classification.md
- DRIFT001  src/frob/app/ticket_runner/_verify.py
- E501  src/frob/app/ticket_runner/_verify.py
- LANG004  src/frob/lang/_support.py
- PERF002  tests/unit/test_main_entry.py
- PERF003  src/frob/gates/_debt_deprecated.py
- PERF003  src/frob/vet/_capability_core.py
- PERF004  src/frob/app/ticket_runner/_new.py
- PERF004  src/frob/scaffold/_skills_sync.py
- PERF004  src/frob/testing/_collect_kotlin.py
- PII012  tests/test_capability_registry.py
- RENDER001  src/frob/release/_cli.py
- SEC110  src/frob/app/ticket_runner/_verify.py
- SEC110  src/frob/app/verify_runner.py
- SEC110  tests/test_release.py
- SELFAUDIT001  design
- TEST001  src/frob/strata/_multifile.py
- TICK003  tickets.md
- TICK004  tickets.md
- WIRE002  tests/unit/test_app_runners_batch6.py
- WIRE003  docs/modules/cli.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  src/frob/release/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/app/fmt_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/gates/_refs_schema.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/strata/_multifile.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1205  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1235  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1397  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1526  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-1688  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-2344  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-2348  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV003  tickets/T-2365  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC001  docs/commands/release.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC002  src/frob/gates/_refs_schema.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC005  docs/modules/cli.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC008  docs/modules/gates.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/design/gate-semantics-classification.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DRIFT001  src/frob/app/ticket_runner/_verify.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  src/frob/app/ticket_runner/_verify.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- LANG004  src/frob/lang/_support.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF002  tests/unit/test_main_entry.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/gates/_debt_deprecated.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF003  src/frob/vet/_capability_core.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/scaffold/_skills_sync.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PERF004  src/frob/testing/_collect_kotlin.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- PII012  tests/test_capability_registry.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- RENDER001  src/frob/release/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  src/frob/app/ticket_runner/_verify.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  src/frob/app/verify_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SEC110  tests/test_release.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SELFAUDIT001  design  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TEST001  src/frob/strata/_multifile.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK003  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE002  tests/unit/test_app_runners_batch6.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE003  docs/modules/cli.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-18: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (ARCH103 src/frob/release/_cli.py, COV001 src/frob/app/fmt_runner.py, COV001 src/frob/gates/_refs_schema.py, COV001 src/frob/strata/_multifile.py, COV003 tickets/T-1205, COV003 tickets/T-1235, COV003 tickets/T-1397, COV003 tickets/T-1526, COV003 tickets/T-1688, COV003 tickets/T-2344, COV003 tickets/T-2348, COV003 tickets/T-2365, DOC001 docs/commands/release.md, DOC002 src/frob/gates/_refs_schema.py, DOC005 docs/modules/cli.md, DOC008 docs/modules/gates.md, DOC011 docs/design/gate-semantics-classification.md, DRIFT001 src/frob/app/ticket_runner/_verify.py, E501 src/frob/app/ticket_runner/_verify.py, LANG004 src/frob/lang/_support.py, PERF002 tests/unit/test_main_entry.py, PERF003 src/frob/gates/_debt_deprecated.py, PERF003 src/frob/vet/_capability_core.py, PERF004 src/frob/app/ticket_runner/_new.py, PERF004 src/frob/scaffold/_skills_sync.py, PERF004 src/frob/testing/_collect_kotlin.py, PII012 tests/test_capability_registry.py, RENDER001 src/frob/release/_cli.py, SEC110 src/frob/app/ticket_runner/_verify.py, SEC110 src/frob/app/verify_runner.py, SEC110 tests/test_release.py, SELFAUDIT001 design, TEST001 src/frob/strata/_multifile.py, TICK003 tickets.md, TICK004 tickets.md, WIRE002 tests/unit/test_app_runners_batch6.py, WIRE003 docs/modules/cli.md) is absent from a full unscoped `frob check --json` run that completed with no budget deferral and no failed/silent tool stage at T-2366's deferred sweep (T-2521: this drop only fires when that measurement itself completed -- no budget deferral, no failed/silent tool stage -- never on an unmeasured or partial run), i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
