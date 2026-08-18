---
id: T-2392
title: no CLI verb amends a ticket body, forcing agents to hand-edit the ledger
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_setters.py
- src/frob/tickets/_models.py
- src/frob/tickets/__init__.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/_cli_parsers/_ticket/__init__.py
- src/frob/app/ticket_runner/_mutate.py
- src/frob/app/ticket_runner/__init__.py
- src/frob/app/config.py
- docs/modules/app.md
- docs/modules/tickets-data-storage.md
- docs/modules/tickets.md
- tests/test_tickets_body.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_setters.py
  reason: 'T-2392: add frob ticket body verb for validated body amendment (front door
    replacing the hand-edit forced by no CLI verb)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/tickets/_models.py
  reason: 'T-2392: add frob ticket body verb for validated body amendment (front door
    replacing the hand-edit forced by no CLI verb)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: 'T-2392: add frob ticket body verb for validated body amendment (front door
    replacing the hand-edit forced by no CLI verb)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_cli_parsers/_ticket/_metadata.py
  reason: 'T-2392: add frob ticket body verb for validated body amendment (front door
    replacing the hand-edit forced by no CLI verb)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/_cli_parsers/_ticket/__init__.py
  reason: 'T-2392: add frob ticket body verb for validated body amendment (front door
    replacing the hand-edit forced by no CLI verb)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_mutate.py
  reason: 'T-2392: add frob ticket body verb for validated body amendment (front door
    replacing the hand-edit forced by no CLI verb)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/__init__.py
  reason: 'T-2392: add frob ticket body verb for validated body amendment (front door
    replacing the hand-edit forced by no CLI verb)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/config.py
  reason: 'T-2392: add frob ticket body verb for validated body amendment (front door
    replacing the hand-edit forced by no CLI verb)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/app.md
  reason: 'T-2392: docs + evidence coverage for the new body verb'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-data-storage.md
  reason: 'T-2392: docs + evidence coverage for the new body verb'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-2392: docs + evidence coverage for the new body verb'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_tickets_body.py
  reason: 'T-2392: docs + evidence coverage for the new body verb'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_tickets_body.py::TestBodyAmend::test_append_appends_text
- tests/test_tickets_body.py::TestBodyAmend::test_set_replaces_text
- tests/test_tickets_body.py::TestBodyAmend::test_reason_missing_refuses
- tests/test_tickets_body.py::TestBodyAmend::test_append_records_body_change_entry
- tests/test_tickets_body.py::TestBodyAmend::test_positive_control_priority_reason_still_required
- tests/test_tickets_body.py::TestBodyCli::test_cli_append_writes_body
- tests/test_tickets_body.py::TestBodyCli::test_cli_missing_text_exits_nonzero
designated_repro_test: tests/test_tickets_body.py::TestBodyCli::test_cli_append_writes_body
acceptance:
- text: Given an existing ticket, when a maintainer or agent needs to add a directive
    to its free-text body, then a frob ticket CLI verb writes it through the validated
    mutation path with a recorded audit trail, and no hand-edit of tickets/T-####/ticket.md
    is required.
  evidence:
  - tests/test_tickets_body.py::TestBodyCli::test_cli_append_writes_body
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED TODAY: two independent agents (Series U twice, Series V once)
hit the same wall and resolved it the same unsafe way.

There is NO CLI verb to edit a ticket's free-text body after creation.
`frob ticket new` takes `--body`/`--body-file`; nothing amends it later.
When the documented remedy for a gate refusal is "add a directive to the
ticket body" (see T-2392 for the BUG002 case), the only available action
is to hand-edit `tickets/T-####/ticket.md` and commit it.

WHY THIS IS SERIOUS, NOT COSMETIC. Hand-editing the ledger is the exact
action this repo learned to forbid the hard way: a space-hash typed into
ledger prose once broke the YAML and took EVERY gate down. The tooling
is currently forcing agents into the one operation the process rules
prohibit, which means the rule cannot hold. Three hand-edits happened
today alone, all by careful agents who disclosed them.

FIX: a `frob ticket body T-#### --append TEXT|--append-file PATH`
(and/or `--set`) verb that writes through the same validated path every
other ticket mutation uses, so the YAML front matter and the free-text
body cannot be desynced by hand. Follow T-2353's precedent, which added
`--reason` to priority/kind/component/tier with a `triage_changes`
audit trail -- a body amendment deserves the same recorded trail.