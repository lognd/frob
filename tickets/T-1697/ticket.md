---
id: T-1697
title: 'frob verify: surface the unverified window -- depth, age, quarantine, attribution'
state: queued
kind: ux
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1687
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/app/verify_runner.py
- src/frob/_cli_parsers/_verify.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: verification
labels:
- watermark-epic
---
An unverified window nobody can see is a liability pretending to be a
feature. This is the leaf that makes the whole epic auditable, and it is
high priority despite being "just CLI": every other leaf's failure mode
is discovered through this surface.

`frob verify status`: the watermark commit and its age, unverified depth,
the oldest unverified entry, quarantine state with the batch and findings
that raised it, and the last batch's outcome including anything
UNATTRIBUTED. Human-readable by default, `--json` for agents.

`frob verify now`: drain and verify synchronously, for a human who wants
the window closed before walking away.

`frob verify explain <finding>`: print the attribution path -- the
reachability chain that assigned this finding to this commit -- so an
attribution can be audited rather than trusted.

Porcelain rule: exit non-zero when quarantine is raised, so a shell or CI
step can gate on "is this repo's verification healthy" without parsing
prose.

Acceptance: `status` reports depth/age/quarantine accurately against a
seeded queue; `--json` round-trips through a pydantic model; a raised
quarantine exits non-zero; `explain` prints a reachability path for an
attributed finding.

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