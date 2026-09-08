---
id: T-4316
title: Closing T-4298 stranded its own frob:todo directive, failing the gate step
state: queued
kind: bug
origin: human
created: '2026-09-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_land_format.py
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
CLOSING A TICKET STRANDED A DEFERRED-WORK DIRECTIVE THAT NAMED IT, FAILING THE
GATE STEP. THIS IS THE SECOND INSTANCE OF THIS EXACT CLASS TODAY.

THE FAILURE. The unscoped gate run reports one TODO002 error: a deferred-work
directive in the land-formatting gate's own module names the ticket that
introduced that module, and that ticket is now closed, so the directive is no
longer bound to an open ticket. Nobody edited the directive or the code around it;
the ticket closing is what broke it.

THE IDENTICAL SHAPE ALREADY HAPPENED HOURS EARLIER with a waiver rather than a
deferred-work marker: a waiver naming a ticket as its follow-up started failing
the moment that ticket closed, and was repaired separately. Two different directive
families, one mechanism -- a comment names a ticket id, the ticket reaches a
terminal state, and a gate that requires the id to be open turns red with no code
change. Expect more of these; several directive families in this codebase can name
a ticket.

DECIDE WHAT THE DIRECTIVE ACTUALLY MEANS BEFORE REBINDING IT. Read what the marked
work is. If the deferred work is genuinely still outstanding, it needs a real open
ticket describing it, and that ticket is the correct binding -- do not point it at
an unrelated open id to clear the error. If the work was in fact completed as part
of the closing ticket and the marker is simply residue, the right fix is deleting
the marker, not rebinding it. Say which you found and why.

THEN ADDRESS THE RECURRENCE, since a second instance in one day of the same
mechanism is the signal. A ticket already exists proposing a warning at close time
for the waiver family; check whether it is filed and whether its framing covers
directive families generally rather than only waivers, and if it does not, say so
in this ticket so the two are not fixed narrowly and separately. Do not build that
check here -- this ticket is the unblock.

VERIFY by running the unscoped gate check and confirming the TODO002 error is gone.
Expect other errors to remain from a separate ticket covering the architecture
gate; those are not yours. Quote the error count you actually see rather than
asserting a clean run.
