---
id: T-2474
title: 'post-land sweep regression from T-2458: 39 new (rule, file) identit(ies),
  50 finding(s) (ARCH103, COV001, COV003, DOC001)'
state: dropped
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/root-write-guard.py
- design
- docs/commands/release.md
- docs/design/gate-semantics-classification.md
- docs/modules/cli.md
- docs/modules/gates.md
- src/frob/app/ticket_runner/_new.py
- src/frob/app/ticket_runner/_query.py
- src/frob/app/verify_runner.py
- src/frob/gates/__init__.py
- src/frob/gates/_debt_deprecated.py
- src/frob/gates/_dup_graph_schema.py
- src/frob/gates/_port_selfcheck.py
- src/frob/gates/_refs_schema.py
- src/frob/release/_cli.py
- src/frob/scaffold/_skills_sync.py
- src/frob/verify/_worker.py
- src/frob/vet/_capability.py
- src/frob/vet/_capability_core.py
- src/frob/vet/_supplychain.py
- tests/test_gates.py
- tests/test_release.py
- tests/unit/test_main_entry.py
- tests/unit/test_ticket_runner_land_release.py
- tickets.md
- tickets/T-1205
- tickets/T-1235
- tickets/T-1397
- tickets/T-1526
- tickets/T-1688
- tickets/T-2344
- tickets/T-2348
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
The deferred post-land unscoped sweep (T-1684) for T-2458 at commit edf1786a8b0f3df7573ec37223a424c2f10f2a6f found 39 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (39), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 50 actual finding(s) across those 39 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH103  .claude/hooks/root-write-guard.py
- ARCH103  src/frob/release/_cli.py
- COV001  src/frob/gates/_port_selfcheck.py
- COV001  src/frob/gates/_refs_schema.py
- COV003  tickets/T-1205
- COV003  tickets/T-1235
- COV003  tickets/T-1397
- COV003  tickets/T-1526
- COV003  tickets/T-1688
- COV003  tickets/T-2344
- COV003  tickets/T-2348
- DOC001  docs/commands/release.md
- DOC002  src/frob/gates/_port_selfcheck.py
- DOC002  src/frob/gates/_refs_schema.py
- DOC005  docs/modules/cli.md
- DOC007  tests/test_gates.py
- DOC008  docs/modules/gates.md
- DOC011  docs/design/gate-semantics-classification.md
- DRIFT002  tests/test_gates.py
- E501  src/frob/app/ticket_runner/_query.py
- E501  src/frob/gates/__init__.py
- E501  src/frob/gates/_dup_graph_schema.py
- E501  src/frob/verify/_worker.py
- F401  src/frob/vet/_capability.py
- LEXCHECK001  src/frob/vet/_supplychain.py
- PERF002  tests/unit/test_main_entry.py
- PERF003  src/frob/gates/_debt_deprecated.py
- PERF003  src/frob/vet/_capability_core.py
- PERF004  src/frob/app/ticket_runner/_new.py
- PERF004  src/frob/scaffold/_skills_sync.py
- RENDER001  src/frob/release/_cli.py
- SEC110  .claude/hooks/root-write-guard.py
- SEC110  src/frob/app/verify_runner.py
- SEC110  tests/test_release.py
- SELFAUDIT001  design
- TICK003  tickets.md
- TICK004  tickets.md
- WIRE003  docs/modules/cli.md
- missing-argument  tests/unit/test_ticket_runner_land_release.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-18: measured false positive: land commit edf1786a (chore(tickets): file T-2472, single-file ticket-ledger add) touches only tickets/T-2472/ticket.md; NONE of the 39 flagged (rule,file) identities overlap with that file. All 39 identities UNATTRIBUTED with empty candidate_commits. Same overlapping identity set (COV003 T-1205/T-1235/T-1397/T-1526/T-1688, TICK003/TICK004 tickets.md which does not exist post-ledger-v2-cutover, SEC110/PERF003/PERF004/DOC011/RENDER001/ARCH103 on unrelated release/gates/verify files) also appears in sibling sweep tickets T-2381/T-2525/T-2560 filed against three DIFFERENT unrelated single-file lands -- diagnostic of stale/non-persisting rolling baseline, not a regression caused by T-2458.
