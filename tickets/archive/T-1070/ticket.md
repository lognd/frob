---
id: T-1070
title: add frob ticket tier CLI verb to mutate an existing ticket's tier
state: dropped
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- src/frob/__main__.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while working T-0936: T-0715 landed the `tier` field (TicketTier
epic|story|ticket) and `frob ticket new --tier` for SETTING tier at
creation time, but never added a mutator verb for an EXISTING ticket
(the `set_priority`/`set_kind`/`set_component` pattern in
src/frob/tickets/__init__.py has no `set_tier` counterpart, and
src/frob/__main__.py/src/frob/app/ticket_runner.py have no `frob ticket
tier <id> <value>` subcommand).

T-0936 (migrate existing EPIC-titled tickets to tier=epic) is scoped to
tickets.md/tickets-archive.md only and is required to use "the real
`frob ticket` CLI verbs for the migration, never hand-edit ledger YAML"
-- but no such verb exists to change an already-created ticket's tier.
T-0936 is blocked on this ticket.

Plan: add `set_tier(root, ticket_id, tier: TicketTier) -> Result[Ticket,
TicketError]` in src/frob/tickets/__init__.py mirroring
`set_component`/`set_priority` (single-writer, ledger-locked
`_set_ticket_field` pattern), a `frob ticket tier <id> <epic|story|
ticket>` CLI subcommand in src/frob/__main__.py, and its runner wiring
in src/frob/app/ticket_runner.py. Keep the existing structural rules
(epic/story parent-child conventions from T-0715) intact -- this ticket
only adds the missing mutate-in-place verb, it does not change tier
semantics.

## Drop reason
- 2026-07-28: exact duplicate of T-1069 (same title, same body intent) from a filing race