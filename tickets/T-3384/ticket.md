---
id: T-3384
title: fix gate:DOC, gate:DRIFT, gate:SELFAUDIT residue (EO slice)
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
- src/frob/tickets/_leases.py
- docs/commands/check.md
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_check_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: T-3358 holds a live lease on tickets.md; DOC011 finding at tickets.md:99
    deferred until that clears
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Series EO slice of self-gate zero drive: gate:DOC (5), gate:DRIFT (3), gate:SELFAUDIT (5). See T-3346/T-3343 for adjacent EM-owned gates (not touched here).