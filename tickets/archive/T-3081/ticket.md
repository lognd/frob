---
id: T-3081
title: TicketSpec.no_scope_declared silently dropped by new_ticket
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_new_renumber.py
- tests/test_tickets_no_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_no_scope.py
  reason: 'T-3081: add regression test file for the no_scope_declared/no_scope_declared_reason
    (and runs_last_parallel_safe/_reason) round-trip drop bug fixed in _ticket_from_spec

    '
  actor: logan
  at: '2026-08-27'
evidence:
- tests/test_tickets_no_scope.py::TestTicketSpecFieldsSurviveNewTicket::test_no_scope_declared_round_trips_through_new_ticket
- tests/test_tickets_no_scope.py::TestTicketSpecFieldsSurviveNewTicket::test_runs_last_parallel_safe_round_trips_through_new_ticket
designated_repro_test: tests/test_tickets_no_scope.py::TestTicketSpecFieldsSurviveNewTicket::test_no_scope_declared_round_trips_through_new_ticket
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 882362d7a70193c244770e03c232d0eb751db56f
---
Found while fixing T-3037's stale test fixture: `frob.tickets._new_
renumber._ticket_from_spec` (the function `new_ticket` uses to build the
`Ticket` it writes) does not copy `spec.no_scope_declared` or
`spec.no_scope_declared_reason` from `TicketSpec` into the constructed
`Ticket` at all -- both fields are silently dropped, so a caller who
files a ticket via `new_ticket(root, TicketSpec(..., no_scope_declared=
True, no_scope_declared_reason="..."))` (the exact filing-time escape
hatch `TicketSpec`'s own docstring documents, mirroring `frob ticket new
--no-scope --no-scope-reason TEXT`) gets a ticket that still reads
`no_scope_declared=False` once loaded back -- `frob ticket start` then
refuses it with the empty-scope guard (T-2394) even though the caller
declared the empty scope intentional at filing time.

Reproduced directly: build a `TicketSpec(no_scope_declared=True,
no_scope_declared_reason="...")`, call `new_ticket`, reload the written
ticket -- `ticket.no_scope_declared` reads `False`.

`_ticket_from_spec` (src/frob/tickets/_new_renumber.py) copies most other
spec fields (scope, scope_breadth_ack/scope_breadth_ack_reason, etc.)
onto the `Ticket(...)` call but has no `no_scope_declared`/
`no_scope_declared_reason` lines at all -- looks like a plain omission
from whenever T-2394 added the field to `TicketSpec`, since `Ticket`
itself has the field and the CLI mutate path (`set_no_scope_declared`)
sets it correctly; only the filing-time `TicketSpec` path is affected.

FIX DIRECTION: add
    no_scope_declared=spec.no_scope_declared,
    no_scope_declared_reason=spec.no_scope_declared_reason,
to the `Ticket(...)` construction in `_ticket_from_spec`, plus a
regression test asserting a `TicketSpec(no_scope_declared=True, ...)`
round-trips through `new_ticket` with the field set.