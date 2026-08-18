---
id: T-2394
title: an empty ticket scope is only caught at land time
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given an implementation ticket with an empty scope, when frob ticket start
    runs, then it refuses, rather than the omission surfacing hours later at land
    time.
  evidence: []
- text: Given a ticket that legitimately has no file scope, when it declares that
    explicitly, then it starts cleanly and is distinguishable from one whose scope
    was merely omitted.
  evidence: []
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED TODAY: T-2358 was created with an EMPTY scope. Nothing
complained at creation, nothing complained at `ticket start`, and
nothing complained during hours of implementation work. It surfaced only
at LAND time, when the out-of-scope waive-deletion check refused, by
which point the agent had to reconstruct the scope from the files it had
already touched and disclose the change.

An empty scope is never correct for an implementation ticket: scope is
simultaneously the evidence-coverage declaration and the write lease, so
an empty one means the ticket holds no lease and its changes are
unattributable. The cost is paid at the most expensive possible moment.

FIX: refuse (or loudly warn on) an empty scope at `frob ticket new` for
implementation kinds, and refuse at `frob ticket start` unconditionally
-- start is the point where a lease is actually needed, so it is the
correct hard gate. Tickets that legitimately have no file scope (a
tier=epic rollup, a pure decision record) should be able to say so
explicitly rather than by omission, so an empty scope and a declared
no-scope are distinguishable. That distinction is the same
fail-loudly doctrine as T-2391: absence must be declared, not inferred
from silence.
