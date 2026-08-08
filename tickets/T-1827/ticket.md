---
id: T-1827
title: SCOPE001/COV002 implicit-ledger-in-scope rule ignores v2 per-ticket tickets/<id>/ticket.md
state: queued
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_models.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
LEDGER_PATH = "tickets.md" (frob.tickets._models) is hardcoded and always appended to a ticket's scope globs (T-0241's implicit-ledger-in-scope rule), but in v2 ticket-store mode each ticket owns tickets/<id>/ticket.md instead of a shared tickets.md monofile. scope_matches never treats a ticket's own tickets/<id>/ticket.md as implicitly in scope in v2 mode, so any v2-mode ticket's own start/scope/sweep bookkeeping touching its own ticket.md fires a spurious SCOPE001 (found while working T-1761: 'SCOPE001: tickets/T-1761/ticket.md is outside T-1761's declared scope' on a completely unrelated file). Fix: scope_matches (and/or _scope_globs) should also implicitly match f"tickets/{ticket.id}/ticket.md" when the store is in v2 mode, mirroring the LEDGER_PATH pattern.