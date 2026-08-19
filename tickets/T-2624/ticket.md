---
id: T-2624
title: CLI wiring for runs_last_parallel_safe
state: queued
kind: feature
origin: human
created: '2026-08-19'
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
- src/frob/__main__.py
- src/frob/app/config.py
- src/frob/app/ticket_runner/__init__.py
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
T-2579 (M4b) added Ticket.runs_last_parallel_safe / _reason (bool+reason
pair, same shape scope_breadth_ack/scope_breadth_ack_reason already
uses) and the MILE004 gate that reads it, but wiring a way to actually
SET the field was out of T-2579's declared scope (src/frob/gates/
_milestone.py, src/frob/gates/__init__.py, src/frob/tickets/_models.py
only -- no _setters.py, _new_renumber.py, _mutate.py/_lifecycle.py).

Needed: a retroactive setter set_runs_last_parallel_safe(root,
ticket_id, reason) in src/frob/tickets/_setters.py (same
_set_ticket_field-adjacent pattern set_scope_breadth_ack uses) plus a
frob ticket runs-last-parallel-safe <id> --reason TEXT CLI verb wired
the same way frob ticket scope-ack is; and frob ticket new
--runs-last-parallel-safe --runs-last-parallel-safe-reason TEXT for
filing-time declaration (TicketSpec already carries both fields).

Until this lands, runs_last_parallel_safe can only be set by directly
constructing a Ticket/editing the ledger file, which is how T-2579's
own tests exercise MILE004 -- fine for gate-logic verification, not fine
for a real operator declaring two runs-last tickets parallel-safe.
