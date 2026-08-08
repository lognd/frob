---
id: T-1836
title: SCOPE001 fires on every ticket's own tickets/T-XXXX/ticket.md (stale LEDGER_PATH)
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
`frob.tickets._models.LEDGER_PATH` is hardcoded to `"tickets.md"` and is
the ONLY file `scope_matches`'s "always implicitly in scope" rule covers
(T-0241). This repo has migrated to per-ticket directories
(`tickets/T-XXXX/ticket.md`) as the file the `frob ticket` CLI actually
writes to for state transitions, scope changes, and Done reports -- but
`LEDGER_PATH` was never updated to match, so every single ticket's own
`tickets/T-XXXX/ticket.md` trips SCOPE001 (T-1787 hit this directly: `frob
check --ticket T-1787` reported `SCOPE001: tickets/T-1787/ticket.md is
outside T-1787's declared scope`) unless the ticket's author manually adds
`tickets/T-XXXX/**` to its own scope, which nothing prompts them to do.

Found while working T-1787 (dispatch telemetry wiring); worked around
locally there via an explicit `frob ticket scope T-1787 --add
'tickets/T-1787/**'`, but every other ticket in this repo has the same
latent gap.

Fix: `LEDGER_PATH`/`scope_matches` (`src/frob/tickets/_models.py`) should
recognize a ticket's own `tickets/<ticket.id>/**` path as always-in-scope,
the same way it already does for the legacy `tickets.md` aggregator file.

## Failure log
- 2026-08-08 attempt 1: Already fixed by T-1817 (_b9_exempt_file exempts tickets/<id>/* in gates/__init__.py) and T-1819 (scope_matches gained ticket_id param, treats tickets/<id>/** implicitly in scope; wired at _scope_gate_check_file, gates/__init__.py:3521). Verified: frob check --only scope --ticket T-1836 reports 0 SCOPE001 errors on src/frob/tickets/_models.py; tests/test_tickets.py::TestScopeMatching::test_own_shard_always_in_scope already covers this. Duplicate T-1827 dropped, absorbed-by this ticket. No code change needed.
