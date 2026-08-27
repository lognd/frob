---
id: T-3051
title: 'Land H4: the quarantine deadlock is UNFIXED -- _dispose_to_existing_duplicate_or_none
  handles DuplicateTicket but not DuplicateFinding'
state: in-progress
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- docs/modules/tickets-verify-sweep.md
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: 'H4 fix: handle DuplicateFinding in dispose-to-existing-duplicate path'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: doc edges for touched symbols in scope
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: evidence tests for the H4 fix
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
