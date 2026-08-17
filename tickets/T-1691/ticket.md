---
id: T-1691
title: Bisect the unattributable residue of a red batch
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: medium
blocked_by:
- T-1690
parent: T-1686
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/_bisect.py
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: 'T-1780: docs/modules/tickets.md was split by subject; this ticket''s own
    touched code lives in the verify/sweep cluster, so its scope now names docs/modules/tickets-verify-sweep.md
    instead of the monofile every other unrelated ticket also held a lease on'
  actor: logan
  at: '2026-08-16'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'T-1780: docs/modules/tickets.md was split by subject; this ticket''s own
    touched code lives in the verify/sweep cluster, so its scope now names docs/modules/tickets-verify-sweep.md
    instead of the monofile every other unrelated ticket also held a lease on'
  actor: logan
  at: '2026-08-16'
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
anchor: false
anchor_reason: null
land_commit: null
---
Tier 3 of the attribution ladder: the fallback for findings the symbolic
tier honestly could not attribute.

Bisect the batch over the single failing finding identity -- log2(N)
verifications, each scoped to re-checking THAT finding rather than
re-running the full gate pass. Scoping matters: a full check per bisect
step makes the fallback cost more than the batching saved, which would
make the whole epic a wash on any batch that ever goes red.

Bisect in a scratch worktree at each candidate commit; never move the
root checkout, which other agents are actively landing against. This is
the same isolation discipline `_capture_pre_land_baseline` already uses,
and it should reuse that machinery rather than growing a second
worktree-snapshot implementation.

Bounded: a step budget and a wall-clock budget, both configurable, both
logged when hit. On exhaustion, file the finding as UNATTRIBUTED against
the whole batch, naming every candidate commit -- a bounded honest answer
beats an unbounded search, and an exhausted bisect that silently reports
success is the failure mode to design against.

Acceptance: a batch with one known-bad commit and no symbolic attribution
converges to that commit within log2(N) scoped verifications; an
exhausted budget files an UNATTRIBUTED finding naming all candidates.

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