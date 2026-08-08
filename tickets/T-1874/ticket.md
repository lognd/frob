---
id: T-1874
title: land() has no skip-close path for a non-terminal anchor ticket's own record
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
- src/frob/tickets/_land_finalize.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1856 added `Ticket.anchor`/`set_anchor` and a land-time refusal
(`_refuse_anchor_terminal_land`) that stops an anchor=True ticket from
landing to a TERMINAL state (done/dropped). What it did not add: a way
to land a non-terminal (queued/in-progress/blocked) anchor ticket's OWN
ledger record at all.

`frob ticket land` ALWAYS attempts a DONE transition
(`_close_finalized_ticket` in src/frob/tickets/_land_finalize.py) unless
`_skip_close_for_terminal_shortcut` recognizes one of exactly two shapes:
DROPPED-with-a-drop-reason, or QUEUED-with-a-recorded-failure-log
(`_skip_close_for_legitimate_drop`/`_skip_close_for_legitimate_fail`,
T-1701/T-1818). There is no third shape for "this ticket is
intentionally staying open forever (anchor=True) and this land is
publishing a scope/evidence/anchor-marker change, not a close attempt."

OBSERVED on T-1778 (2026-08-08): after `set_anchor(..., anchor=True,
...)` plus `frob ticket requeue` (to release the lease, no more active
work), `frob ticket land T-1778` failed with `InvalidTransition: queued
-> done` -- exactly the T-1818 incident shape T-1818 itself already
fixed for the fail-log case, but for an anchor marker instead. Worked
around by recording a `frob ticket fail` attempt (piggybacking on the
existing QUEUED-with-failure-log skip) purely to get land to publish the
record -- semantically wrong (nothing about the anchor marker is a
"failed attempt"), but the only mechanism land() currently offers.

FIX: add `_skip_close_for_anchor_no_close_requested` (or fold into
`_skip_close_for_terminal_shortcut`) recognizing `current.anchor is True
and current.state is not TicketState.IN_PROGRESS` (or some equivalent
"not actively mid-work" signal) as a third skip-close shape, publishing
the ledger record as-is with a WARNING log naming the anchor, mirroring
the drop/fail precedent exactly. Scope: src/frob/tickets/_land_finalize.py
(possibly src/frob/tickets/_models.py if a new signal field is needed).
