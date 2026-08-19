---
id: T-2640
title: 'post-land sweep regression from T-2623: 43 new (rule, file) identit(ies),
  64 finding(s) (ARCH103, COV001, COV003, COV004)'
state: queued
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design
- docs/commands/release.md
- docs/modules/cli.md
- docs/modules/gates.md
- src/frob/app/fmt_runner.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/verify_runner.py
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_milestone.py
- src/frob/gates/_refs_schema.py
- src/frob/gates/_rule_id_scan.py
- src/frob/lang/_support.py
- src/frob/release/_cli.py
- src/frob/scaffold/_skills_sync.py
- src/frob/strata/_multifile.py
- src/frob/testing/_collect_kotlin.py
- src/frob/tickets/__init__.py
- src/frob/tickets/_store.py
- src/frob/vet/_capability_core.py
- tests/test_capability_registry.py
- tests/test_release.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_main_entry.py
- tickets.md
- tickets/T-1397
- tickets/T-1526
- tickets/T-1688
- tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
- tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md
- tickets/T-2344
- tickets/T-2348
- tickets/T-2365
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
The deferred post-land unscoped sweep (T-1684) for T-2623 at commit cca8edb735a36006e70b0b6542b4bb580a0c5ca3 found 43 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (43), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 64 actual finding(s) across those 43 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH103  src/frob/release/_cli.py
- ARCH103  src/frob/tickets/_store.py
- COV001  src/frob/app/fmt_runner.py
- COV001  src/frob/gates/_refs_schema.py
- COV001  src/frob/gates/_rule_id_scan.py
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
- DOC002  src/frob/gates/_milestone.py
- DOC002  src/frob/gates/_refs_schema.py
- DOC005  docs/modules/cli.md
- DOC006  tickets/T-2570/ticket.md
- DOC008  docs/modules/gates.md
- DOCENUM001  docs/modules/gates.md
- DRIFT001  src/frob/app/ticket_runner/_verify.py
- DRIFT001  src/frob/tickets/__init__.py
- F401  src/frob/app/ticket_runner/__init__.py
- LANG004  src/frob/lang/_support.py
- PERF002  tests/unit/test_main_entry.py
- PERF003  src/frob/gates/_debt_deprecated.py
- PERF003  src/frob/vet/_capability_core.py
- PERF004  src/frob/app/ticket_runner/_new.py
- PERF004  src/frob/gates/_milestone.py
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

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.