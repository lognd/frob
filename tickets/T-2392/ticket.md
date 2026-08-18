---
id: T-2392
title: no CLI verb amends a ticket body, forcing agents to hand-edit the ledger
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given an existing ticket, when a maintainer or agent needs to add a directive
    to its free-text body, then a frob ticket CLI verb writes it through the validated
    mutation path with a recorded audit trail, and no hand-edit of tickets/T-####/ticket.md
    is required.
  evidence: []
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
