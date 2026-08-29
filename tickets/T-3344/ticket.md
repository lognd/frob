---
id: T-3344
title: Clear gate:DRIFT findings (53 errors) for release gate
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/gates.md
- src/frob/app/check_runner.py
- src/frob/app/doctor_runner.py
- src/frob/ci_report.py
- src/frob/gates/_comment_placement.py
- src/frob/gates/_docstring_archaeology.py
- src/frob/ghio.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_check.py
- tests/unit/test_close_blocked_by_guard.py
- tests/unit/test_doctor_runner_t1276.py
- tests/unit/test_logging_module.py
- tests/unit/test_reopen_ticket.py
- scripts/fleet_status.py
- src/frob/doctor.py
- src/frob/tickets/_land_squash.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: '**/*'
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/gates.md
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/check_runner.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/ci_report.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_comment_placement.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_docstring_archaeology.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/ghio.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_check.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_close_blocked_by_guard.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_doctor_runner_t1276.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_logging_module.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_reopen_ticket.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: scripts/fleet_status.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/doctor.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_land_squash.py
  reason: narrow to actual touched files for T-3344 (gate:DRIFT cleanup); the doable/start
    command initially rejected **/* as over-broad
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Sprint task: reduce unscoped frob check DRIFT errors from 53 to 0. Investigate histogram of rule ids/files first; fix real doc drift, frob ack verified-correct docs, never mass-ack.