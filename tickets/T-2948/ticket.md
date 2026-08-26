---
id: T-2948
title: DirtyMain owner classifier blames a sibling ticket that merely declares overlapping
  scope, blocking the ticket actually being landed
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-2948: per-path fix to the CrossTicketLeakage sibling-attribution scan
    (_leaked_hits_for_candidate) -- a sibling that only declares scope over a path
    but never actually committed a change to it must not misattribute a hit for that
    path'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-2948: per-path fix to the CrossTicketLeakage sibling-attribution scan
    (_leaked_hits_for_candidate) -- a sibling that only declares scope over a path
    but never actually committed a change to it must not misattribute a hit for that
    path'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-2948: doc anchor for _check_cross_ticket_leakage/_leaked_hits_for_candidate
    that this fix touches'
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
