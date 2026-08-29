---
id: T-3342
title: Fix gate:DOC errors (DOC001-007 cluster)
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
- src/frob/app/check_runner.py
- src/frob/app/doctor_runner.py
- src/frob/ci_report.py
- src/frob/gates/_comment_placement.py
- src/frob/gates/_docstring_archaeology.py
- src/frob/ghio.py
- src/frob/tickets/_leases.py
- tests/unit/test_app_runners_batch6.py
- tests/unit/test_check.py
- tests/unit/test_close_blocked_by_guard.py
- tests/unit/test_doctor_runner_t1276.py
- tests/unit/test_logging_module.py
- tests/unit/test_reopen_ticket.py
- docs/guides/release.md
- docs/index.md
- docs/modules/cli.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: '**/*.py'
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: docs/**
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: tickets/**
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/check_runner.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/app/doctor_runner.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/ci_report.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_comment_placement.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_docstring_archaeology.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/ghio.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/tickets/_leases.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_app_runners_batch6.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_check.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_close_blocked_by_guard.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_doctor_runner_t1276.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_logging_module.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/test_reopen_ticket.py
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/guides/release.md
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/index.md
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/cli.md
  reason: narrow to the exact 16 files this ticket touched for the gate:DOC fix
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): purely doc-directive/content fixes for gate:DOC
    findings (frob:tests target-form syntax, frob:doc anchor slug, dead ticket citation,
    stale generated table, orphaned doc link) -- no executable code path changed,
    confirmed via py_compile on every touched .py file'
  actor: logan
  at: '2026-08-29'
  old_length: 136
  new_length: 432
- mode: append
  reason: 'BUG002 front door (T-2393): purely doc-directive/content fixes for gate:DOC
    findings (frob:tests target-form syntax, frob:doc anchor slug, dead ticket citation,
    stale generated table, orphaned doc link) -- no executable code path changed,
    confirmed via py_compile on every touched .py file'
  actor: logan
  at: '2026-08-29'
  old_length: 432
  new_length: 728
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Series EH: unscoped self-gate DOC cluster at 50 errors. Investigate root causes (rule histogram, archived-ticket doc pointers) then fix.

frob:no-behavior-change reason="purely doc-directive/content fixes for gate:DOC findings (frob:tests target-form syntax, frob:doc anchor slug, dead ticket citation, stale generated table, orphaned doc link) -- no executable code path changed, confirmed via py_compile on every touched .py file"

frob:no-behavior-change reason="purely doc-directive/content fixes for gate:DOC findings (frob:tests target-form syntax, frob:doc anchor slug, dead ticket citation, stale generated table, orphaned doc link) -- no executable code path changed, confirmed via py_compile on every touched .py file"