---
id: T-3325
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3273):
  13 new (rule, file) identit(ies) (SUPPRESS001, invalid-argument-type, invalid-assignment,
  unresolved-attribute)'
state: queued
kind: bug
origin: agent
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/__main__.py
- tests/test_ci_report.py
- tests/test_tickets.py
- tests/test_tickets_acceptance.py
- tests/test_tickets_brief.py
- tests/test_tickets_velocity.py
- tests/test_vet.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_main_entry.py
- tests/unit/verify/test_backpressure.py
findings:
- - SUPPRESS001
  - tests/test_ci_report.py
- - SUPPRESS001
  - tests/test_tickets.py
- - SUPPRESS001
  - tests/test_tickets_acceptance.py
- - SUPPRESS001
  - tests/test_tickets_brief.py
- - SUPPRESS001
  - tests/test_tickets_velocity.py
- - SUPPRESS001
  - tests/unit/verify/test_backpressure.py
- - invalid-argument-type
  - src/frob/__main__.py
- - invalid-argument-type
  - tests/unit/test_app_runners_batch6.py
- - invalid-assignment
  - tests/test_ci_report.py
- - invalid-assignment
  - tests/test_tickets_velocity.py
- - invalid-assignment
  - tests/test_vet.py
- - invalid-assignment
  - tests/unit/verify/test_backpressure.py
- - unresolved-attribute
  - tests/unit/test_main_entry.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3273) at commit fb4bc3870c17ecd25a58a2d711dafc86725f8687 found 13 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- SUPPRESS001  tests/test_ci_report.py
- SUPPRESS001  tests/test_tickets.py
- SUPPRESS001  tests/test_tickets_acceptance.py
- SUPPRESS001  tests/test_tickets_brief.py
- SUPPRESS001  tests/test_tickets_velocity.py
- SUPPRESS001  tests/unit/verify/test_backpressure.py
- invalid-argument-type  src/frob/__main__.py
- invalid-argument-type  tests/unit/test_app_runners_batch6.py
- invalid-assignment  tests/test_ci_report.py
- invalid-assignment  tests/test_tickets_velocity.py
- invalid-assignment  tests/test_vet.py
- invalid-assignment  tests/unit/verify/test_backpressure.py
- unresolved-attribute  tests/unit/test_main_entry.py

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Failure log
- 2026-08-30 attempt 1: already resolved on main: frob check --only ty --ticket T-3325 and --only suppress --ticket T-3325 both zero-match all 13 identities (no SUPPRESS001 in the 6 test files, no invalid-argument-type/invalid-assignment/unresolved-attribute in the 4 python files)
