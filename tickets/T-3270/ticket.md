---
id: T-3270
title: frob ticket land's fixed wall-clock timeout races variable-cost contention,
  killing progressing lands
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
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
found while working T-3256 (frob check admission budget) and directly from coordinator-
supplied field evidence during that ticket.

MEASURED 2026-08-28 (coordinator, Series DP's frob ticket land T-3246): the land's own
`timeout 540` wrapper killed it at the wall clock while its child `frob check --ticket
T-3246` was 335s in at 82.8% CPU -- actively progressing, not stalled, not deadlocked. Six
concurrent series were landing/checking at once (this repo's own recorded operational
condition, see T-3256). T-3246 was left `state: in-progress` with no land commit (this
time; this repo also has a recorded failure mode where a timed-out land writes `state:
done` with evidence while ZERO code reaches main, which is worse).

This implementer independently reproduced the identical shape three times in a row while
landing T-3254 under the same box conditions: `frob ticket land T-3254` killed by its own
540s wrapper with no process left alive afterward (Terminated, exit 124), the ticket left
closed-but-unlanded.

THE GAP: `frob ticket land`'s wall-clock budget is FIXED (this repo's own house rule
mandates `timeout 540`), but how long a land's child `frob check` needs is NOT fixed --
it depends on how many other checks are concurrently competing for the box (T-3256's own
finding: N concurrent checks is an N-fold oversubscription). A fixed timeout racing a
variable-cost operation means legitimate, progressing work gets killed under load, not
just genuinely wedged work.

WHAT TO BUILD -- measure before choosing: whether `frob ticket land`'s own internal timeout
handling (distinct from the external shell `timeout 540` wrapper, which is a house/hook
convention this ticket should NOT try to change) can detect that its child `frob check` is
demonstrably still making progress (CPU time advancing, not blocked) and extend its own
budget accordingly, versus a genuinely wedged check that should still fail fast. State
which mechanism was chosen and why -- do NOT simply raise a fixed number: an unbounded land
is worse than a killed one (the timeout is what makes a genuinely wedged land fail fast),
and a document convention (like T-3256's own operational-rule doctrine) is not a fix.

RELATED, NOT A DUPLICATE: T-2691 (frob ticket land has no externally-pollable progress/
lock-contention status) is about OBSERVABILITY of a running land; this ticket is about the
land's own DEADLINE not being contention-aware. Cross-reference before starting either.
