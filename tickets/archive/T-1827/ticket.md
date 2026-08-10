---
id: T-1827
title: SCOPE001/COV002 implicit-ledger-in-scope rule ignores v2 per-ticket tickets/<id>/ticket.md
state: dropped
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

## Drop reason
- 2026-08-08: Duplicate of T-1836; both describe the same LEDGER_PATH/scope_matches gap for v2 per-ticket tickets/<id>/ticket.md. Already fixed: T-1817 added tickets/<id>/* to _b9_exempt_file, T-1819 added ticket_id param to scope_matches (tickets/<id>/** implicitly in scope), wired at gates/__init__.py:3521's _scope_gate_check_file call. Verified: frob check --only scope --ticket T-1836 reports 0 SCOPE001 errors; tests/test_tickets.py::TestScopeMatching::test_own_shard_always_in_scope already covers it. (absorbed by T-1836)
