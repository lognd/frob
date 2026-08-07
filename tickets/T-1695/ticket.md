---
id: T-1695
title: 'Verify-worker resource budget: never starve foreground agents'
state: queued
kind: feature
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
- src/frob/serve/_daemon.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
---
A permanent background verifier competes with foreground agent work for
CPU and memory. On this box that is not theoretical: the 2026-07-29
session losses were OOM kills, and the standing cap is 3-4 concurrent
agents. An epic that makes lands fast and then OOM-kills the agents doing
them is a net loss.

Required: reduced scheduling priority for the worker and its children
(nice, and ionice where available); a concurrency budget so the worker
never runs while more than N foreground agents hold leases -- the lease
count `frob worktree sweep` and `_profile._concurrent_lease_count`
already read is the right signal, reuse it rather than inventing a second
notion of "how busy is this repo"; and a memory ceiling that defers the
batch rather than being killed by the OOM killer.

Deferral under load must be visible: log at INFO when the worker yields,
naming the lease count and the depth it is yielding at. A worker that
silently never runs is indistinguishable from one that is keeping up,
until the backpressure ceiling trips and nobody knows why.

Acceptance: the worker yields while the lease count is at or above the
configured ceiling and resumes below it; worker children inherit the
reduced priority; each yield is logged with its cause.

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