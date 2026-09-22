---
id: T-5290
title: frob ticket points (and other setters) on an ARCHIVED id materialize a duplicate
  active ticket dir, wedging the ledger with DuplicateId
state: queued
kind: bug
origin: human
created: '2026-09-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
- src/frob/tickets/_store.py
- tests/test_tickets_points.py
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
Observed 2026-09-22: 'frob ticket points T-0838 3' run against an id that lives only in tickets/archive/ created tickets/T-0838/{ticket.md,done-report.md} in the active ledger (commit 962034e085, reverted by the coordinator), after which every ledger write refused with 'id(s) present in both active and archive' (T-3710 class). Setters must refuse an archived id (typani Result, 'archived: reopen first'), never copy the archive record into the active ledger. Positive control: a setter on an archived id returns Err and leaves tickets/ untouched.