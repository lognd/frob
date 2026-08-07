---
id: T-1694
title: 'Crash safety: a dead verify worker must never advance the watermark'
state: queued
kind: bug
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1688
parent: T-1686
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/_worker.py
- src/frob/tickets/_land.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
---
The watermark is a claim that work was done. Every way it can advance
without that work having been done is a correctness hole, and they are
all crash-shaped.

Reuse the T-1523 post-land-verify marker pattern rather than inventing a
second one: write an in-flight marker naming the batch and target commit
before verification begins, clear it after the watermark advances. A
marker found at startup means a worker died mid-verification; that batch
is UNVERIFIED and must be re-queued, never assumed green.

Specific holes to close, each with a test that kills the worker at that
exact point: death between queue read and verification start; between a
green result and the watermark write; between the watermark write and
queue compaction; and a torn watermark write (write-temp-then-rename, so
a partial file is never observable).

Two workers must never verify concurrently for one root -- reuse the
daemon's existing singleton lock, do not add a second exclusion
mechanism.

Acceptance: for each named kill point, the next startup reports the batch
as unverified and re-queues it; the watermark never names a commit whose
verification did not complete.

Standing repo constraints (binding, not restatement):

- SYMBOLIC, NEVER LEXICAL. Every decision this ticket makes about "which
  code does this concern" must go through the symbol/reference graph
  (frob.graph), never a path-string comparison, filename glob, or regex
  over source text. A lexical shortcut here is a latent wrong answer that
  only shows up under refactor.
- Fallible operations return a typani `Result[T, E]` with a named
  `ErrorSet`. Exceptions only for unrecoverable programmer bugs. Never a
  bare `except` that turns an unknown state into a clean one.
- "Cannot verify" is NEVER "verified". Every unmeasurable outcome must be
  distinguishable from a measured-clean one, in the data model and in the
  logs -- this is the single invariant the whole epic rests on.
- Persisted records are pydantic models with `frozen=True, extra="forbid"`,
  versioned, and forward-compatible on read.
- LOG EVERYTHING WORTH LOGGING: every state change, queue transition,
  boundary crossing, branch, and error path gets a module-logger line per
  ~/.claude/refs/logging.md. Never `print`.
- Docs land in the same change as the code. No follow-up docs ticket.
- No waivers. If a gate fires, fix the cause or fix the gate; a waiver
  here is a structural defect, not a resolution.