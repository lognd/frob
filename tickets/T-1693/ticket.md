---
id: T-1693
title: 'Quarantine circuit breaker: a red batch stops further deferred lands until
  attributed'
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: critical
blocked_by:
- T-1690
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/verify/_quarantine.py
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
---
The single most important rule in the epic. Landing on top of a
known-broken base is what makes attribution cost explode: every
subsequent land widens the candidate set and adds findings that are
consequences rather than causes.

On a red batch verification, raise a durable quarantine flag. While
raised, deferred landing is off: a land either runs FULLY SYNCHRONOUS
verification (paying the old cost, which is correct -- the credit line is
suspended, not the work) or blocks, per profile. Ledger-integrity and
LAND-PROOF paths are untouched, as always.

Quarantine clears only when every finding in the red batch is attributed
and filed, or explicitly dismissed by a recorded human decision. It must
NOT clear on a subsequent green verification: a green run after more
lands means the tree is clean NOW, not that the earlier regression was
understood, and auto-clearing on green is how a circuit breaker silently
becomes decoration.

Every raise and clear is logged at ERROR/WARNING with the batch, the
findings, and the clearing reason, and recorded durably so a daemon
restart cannot lose a raised quarantine. A quarantine that evaporates on
restart is worse than none, because it is trusted.

Acceptance: a red batch raises quarantine; a subsequent land does not
defer; a later green verification does NOT clear it; attributing and
filing every finding does; the flag survives a worker restart.

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