---
id: T-3096
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3033):
  15 new (rule, file) identit(ies), 23 finding(s) (SUPPRESS001, invalid-argument-type,
  invalid-assignment, unresolved-attribute)'
state: queued
kind: bug
origin: agent
created: '2026-08-27'
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
- src/frob/app/_config_external.py
- src/frob/app/ticket_runner/_new.py
- tests/test_ci_report.py
- tests/test_tickets.py
- tests/test_tickets_acceptance.py
- tests/test_tickets_brief.py
- tests/test_tickets_velocity.py
- tests/test_vet.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_main_entry.py
- tests/unit/verify/test_backpressure.py
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3033) at commit a42a4ee4c0be34574e352bfdc472494d1979ae18 found 15 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (15), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 23 actual finding(s) across those 15 identit(ies).

New (rule, file) identit(ies) filed here:

- SUPPRESS001  src/frob/app/ticket_runner/_new.py
- SUPPRESS001  tests/test_ci_report.py
- SUPPRESS001  tests/test_tickets.py
- SUPPRESS001  tests/test_tickets_acceptance.py
- SUPPRESS001  tests/test_tickets_brief.py
- SUPPRESS001  tests/test_tickets_velocity.py
- SUPPRESS001  tests/unit/verify/test_backpressure.py
- invalid-argument-type  src/frob/__main__.py
- invalid-argument-type  src/frob/app/_config_external.py
- invalid-argument-type  tests/unit/test_app_runners_batch6.py
- invalid-assignment  tests/test_ci_report.py
- invalid-assignment  tests/test_tickets_velocity.py
- invalid-assignment  tests/test_vet.py
- invalid-assignment  tests/unit/verify/test_backpressure.py
- unresolved-attribute  tests/unit/test_main_entry.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- SUPPRESS001  src/frob/app/ticket_runner/_new.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SUPPRESS001  tests/test_ci_report.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SUPPRESS001  tests/test_tickets.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SUPPRESS001  tests/test_tickets_acceptance.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SUPPRESS001  tests/test_tickets_brief.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SUPPRESS001  tests/test_tickets_velocity.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- SUPPRESS001  tests/unit/verify/test_backpressure.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- invalid-argument-type  src/frob/__main__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- invalid-argument-type  src/frob/app/_config_external.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- invalid-argument-type  tests/unit/test_app_runners_batch6.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- invalid-assignment  tests/test_ci_report.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- invalid-assignment  tests/test_tickets_velocity.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- invalid-assignment  tests/test_vet.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- invalid-assignment  tests/unit/verify/test_backpressure.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- unresolved-attribute  tests/unit/test_main_entry.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.