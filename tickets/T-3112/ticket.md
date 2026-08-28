---
id: T-3112
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3107):
  20 new (rule, file) identit(ies), 38 finding(s) (AFFECT001, COV002, I001, SUPPRESS001)'
state: in-progress
kind: docs
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
- src/frob/app/mutate_runner.py
- src/frob/app/ticket_runner/_new.py
- src/frob/testing/_collect.py
- src/frob/testing/_coverage_refresh.py
- tests/test_ci_report.py
- tests/test_tickets.py
- tests/test_tickets_acceptance.py
- tests/test_tickets_brief.py
- tests/test_tickets_velocity.py
- tests/test_vet.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_main_entry.py
- tests/unit/test_pytest_spawn_env_wiring.py
- tests/unit/verify/test_backpressure.py
- tests/unit/verify/test_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: kind
  old_value: bug
  new_value: docs
  reason: 'pure re-measurement: all 20 (rule,file) identities checked against a fresh
    frob check run and confirmed to NOT reproduce on main -- stale/pre-existing residue,
    nothing to fix, no code surface changed'
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3107) at commit 1ee8d593fdfb7cd8f8a830ecace8de628bde1d64 found 20 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (20), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 38 actual finding(s) across those 20 identit(ies).

New (rule, file) identit(ies) filed here:

- AFFECT001  src/frob/app/mutate_runner.py
- AFFECT001  src/frob/testing/_collect.py
- AFFECT001  src/frob/testing/_coverage_refresh.py
- COV002  tests/unit/test_pytest_spawn_env_wiring.py
- I001  /home/logan/projects/frob/tests/unit/verify/test_quarantine.py
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

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.