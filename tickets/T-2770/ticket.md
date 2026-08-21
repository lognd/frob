---
id: T-2770
title: frob ticket has no parent setter, so a mis-parented ticket cannot be corrected
  without a forbidden ledger hand-edit
state: queued
kind: bug
origin: agent
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_setters.py
- src/frob/_cli_parsers/_ticket/
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
`frob ticket` exposes setters for priority, kind, component, tier, runs-last,
and milestone, but NOT for `parent`. A ticket's parent can therefore only be
set at `frob ticket new` time, and a ticket filed without one -- or with the
wrong one -- cannot be corrected through the CLI at all.

The only remaining route is hand-editing `tickets/T-####/ticket.md`, which is
explicitly forbidden: a hand edit once put a space-hash into prose, broke the
ledger YAML, and took every gate down.

## Measured instance that surfaced this

T-1382 ("Decouple frob from the Makefile") has fired the ticket-rot alarm for
19 days as NEEDS CLOSE, on the rationale that every child is terminal. It is
NOT closeable -- its own decomposition lists five items, and item 4 (the
path/shell portability sweep) is live and unfinished as T-2384 (state=queued,
priority=high, parent=null). Item 2 likewise shipped as the `frob natives
build` ticket family, also unparented.

So the epic's children are all terminal ONLY because the tickets that actually
continue its work were filed with `parent: null`. The rot detector reads child
terminality and concludes "closeable"; the epic's goal is measurably further
away than at filing (Makefile 528 -> 574 lines).

Re-parenting T-2384 to T-1382 is the correct fix and is currently impossible
without a forbidden hand edit.

## Two defects, and they need separating

1. No `parent` setter. This ticket.
2. The rot detector treats "every child terminal" as "epic closeable" without
   consulting whether the epic's stated goal was met. An epic whose successor
   work was filed unparented looks finished. File separately if confirmed;
   verify the detector's actual logic before asserting it.

## Required shape

Mirror `set_runs_last` in `src/frob/tickets/_setters.py` and its CLI parser.
Must REFUSE, not silently accept:
- a parent id that does not exist
- a cycle (A parent B, B parent A, and longer rings)
- a parent whose tier is not strictly above the child's (a `ticket` cannot
  parent an `epic`)
- self-parenting

## Positive controls, both directions

- re-parenting T-2384 to T-1382 succeeds, and T-1382 thereafter reports as
  DECOMPOSED/BEING WORKED rather than NEEDS CLOSE
- each refusal case above FIRES; a legitimate epic->story->ticket edge does NOT
- a ticket that already has a parent can be moved, and the old edge does not
  linger

## Note

Do not "fix" T-1382 by closing it. Its goal is unmet and the line count grew.
