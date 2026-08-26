---
id: T-2965
title: frob ticket set-parent needs a --clear path to detach a mis-parented ticket
  to root
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/_config_external.py
- docs/modules/tickets.md
- tests/test_tickets_parent.py
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
Measured directly while working T-2959: `frob ticket set-parent <id>
<parent-id>` (T-2770, src/frob/tickets/_setters.py::set_parent) has no
route to CLEAR a ticket's parent edge back to `null` -- `parent-id` is
a required positional argument and `_validate_parent_edge` refuses any
value that does not resolve to an existing ticket in the queue
(`TicketError.ParentNotFound`). The function's own docstring confirms
this is by design for its ORIGINAL motivating case (T-2770's own
"successor work filed with `parent: null`... re-parenting the
successor ONTO the epic is the fix" -- one-directional, attach only).

The inverse case has no tooling: a ticket mis-parented under the WRONG
epic, whose correct parent is genuinely `null` (it should be a
top-level/root ticket), cannot be fixed without either (a) hand-editing
`ticket.md` frontmatter directly -- forbidden by this repo's own
playbook and by `_TICKET_FROZEN_FIELDS`-style discipline for every
other ledger-owned field, or (b) inventing a placeholder parent ticket
just to have something valid to point at (T-2959's own workaround: a
brand-new top-level epic, T-2964, was filed specifically so T-2384
had somewhere real to move to -- legitimate in that case because T-2384
genuinely needed a portability-epic home, but NOT a general solution
for a ticket that should have no parent at all, e.g. a genuinely
free-standing bug).

Add a `--clear` (or `--none`/`--detach`) flag to `frob ticket
set-parent` that writes `parent: null` directly, going through the
same reason-required, land-in-progress-refusing, single-writer path
`set_parent` already uses -- not a new bypass. `_validate_parent_edge`
needs no change (a null target skips validation entirely, same as
`Ticket.parent` already defaults to `None` for a ticket filed with no
`--parent`).
