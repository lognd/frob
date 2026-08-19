---
id: T-2625
title: 'worktree classifier: ACTIVE verdict does not distinguish queued-idle from
  a live lease'
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- scripts/fleet_status.py
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
`worktree_content_classification`'s ACTIVE short-circuit (T-2599, refined
T-2617) treats ANY non-terminal ticket state (queued/planned/in-progress)
identically -- a ticket that is merely QUEUED with no live lease held
anywhere reads exactly the same "ACTIVE, never proposed for removal" as
one genuinely in progress right now.

Measured: `t-1599`'s worktree flags ACTIVE while T-1599 is `queued` with
no worktree activity and (per T-2617's own investigation) no indication
anyone is working it. ACTIVE is the safe-direction verdict (never
proposed for removal) so this is lower severity than the STRANDED false
positives T-2617 fixed, but the ticket-state input is only partially
consulted: it distinguishes terminal from non-terminal, not "queued and
idle" from "someone holds a live lease on this ticket right now".

## Fix

Consult `ticket_lease(ticket_id)` (already in this module, T-2133) in
addition to ticket state: a `queued` ticket with NO live lease record
could fall through to the ordinary content test instead of an automatic
ACTIVE, since nobody has actually claimed it. `in-progress`/`planned`
tickets, or any ticket WITH a live lease, keep the current ACTIVE
short-circuit unconditionally.

## Origin

Filed from T-2617's own body: "t-1599 is flagged ACTIVE while T-1599 is
a QUEUED story with no live work... ACTIVE is the safe direction so it
is lower priority... fold it in if cheap, file separately if not." Not
cheap: it needs a second signal (lease presence) beyond what T-2617's own
fix already reads, and mixing it into the STRANDED bug-fix would obscure
BUG002 evidence binding for two unrelated failure modes in one ticket.
