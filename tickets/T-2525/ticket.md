---
id: T-2525
title: 'post-land sweep regression from T-2503: 38 new (rule, file) identit(ies) (ARCH103,
  COV001, COV003, DOC001)'
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
- scripts/fleet_status.py
- src/frob/app/fmt_runner.py
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/app/verify_runner.py
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_refs_schema.py
- src/frob/graph/summary.py
- src/frob/lang/_support.py
- src/frob/release/_cli.py
- src/frob/scaffold/_skills_sync.py
- src/frob/testing/_collect_kotlin.py
- src/frob/vet/_capability_core.py
- tests/test_capability_registry.py
- tests/test_release.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_app_runners_json_guard_t2492.py
- tests/unit/test_main_entry.py
- tests/unit/test_ticket_runner_repro_merge_base.py
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
The deferred post-land unscoped sweep (T-1684) for T-2503 at commit 75f62ad79377f5a1eeb7e700b87ab2081af81095 found 38 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- ARCH103  src/frob/release/_cli.py
- COV001  src/frob/app/fmt_runner.py
- COV001  src/frob/gates/_refs_schema.py
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
- E501  scripts/fleet_status.py
- E501  src/frob/graph/summary.py
- E501  src/frob/testing/_collect_kotlin.py
- F401  tests/unit/test_ticket_runner_repro_merge_base.py
- F811  tests/unit/test_app_runners_json_guard_t2492.py
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
- TICK003  tickets.md
- TICK004  tickets.md
- WIRE002  tests/unit/test_app_runners_batch6.py
- WIRE003  docs/modules/cli.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH103  src/frob/release/_cli.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/app/fmt_runner.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  src/frob/gates/_refs_schema.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
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
- E501  scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  src/frob/graph/summary.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  src/frob/testing/_collect_kotlin.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F401  tests/unit/test_ticket_runner_repro_merge_base.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F811  tests/unit/test_app_runners_json_guard_t2492.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
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
- TICK003  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK004  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE002  tests/unit/test_app_runners_batch6.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- WIRE003  docs/modules/cli.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-18: measured false positive: land commit 75f62ad7 (chore(tickets): file T-2523, single-file ticket-ledger add) touches only tickets/T-2523/ticket.md; NONE of the 38 flagged (rule,file) identities overlap with that file. All 38 UNATTRIBUTED, empty candidate_commits. Identity set overlaps heavily with sibling sweep tickets T-2381/T-2474/T-2560, each filed against different unrelated single-file lands -- diagnostic of a stale/non-persisting rolling baseline (recurring phantom findings, e.g. TICK003/TICK004 against tickets.md which was deleted by the unrelated T-2356 ledger-v2 land and no longer exists on main), not a regression caused by T-2503.
