---
id: T-1696
title: Collapse rapid/standard/fortress into one queue-depth dial and delete the if-rapid
  land seams
state: queued
kind: feature
origin: agent
created: '2026-08-06'
priority: high
blocked_by:
- T-1692
- T-1693
parent: T-1686
tier: ticket
sprint: null
scope:
- src/frob/tickets/_profile.py
- src/frob/app/ticket_runner/_land_cmd.py
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
The payoff leaf, and deliberately LAST: this is a refactor, and it must
land on a mechanism that already works rather than being the thing that
proves it.

Today `rapid` is a scatter of `if effective_profile(...) is RAPID` seams
through the land pipeline -- baseline thread, pre-commit sweep, post-land
sweep, TEST016, REL001, evidence leniency. Each is an independent
opportunity for the profiles to drift out of correspondence, and every
new profile-sensitive behaviour adds another.

After this leaf a profile is a settings record consumed in ONE place:
queue depth ceiling, age ceiling, on-red policy (refuse / quarantine+file
/ file-only), and the never-relaxed set. `fortress` = depth 0 +
refuse-on-red. `standard` = bounded depth + quarantine. `rapid` =
unbounded + file-only. Every land-pipeline branch reads the settings
record; none branches on a profile NAME. A grep for the profile enum
outside the settings module should return nothing, and that is worth a
gate rule of its own if it is cheap to add.

Ledger integrity and LAND-PROOF stay outside the dial entirely, as they
are today -- they are not a setting and must not become expressible as
one.

Migration must be behaviour-preserving per profile, demonstrated by
tests asserting the same observable land behaviour before and after, not
by inspection.

Acceptance: no land-pipeline module branches on ProfileName; each profile
reproduces its current observable behaviour; adding a fourth profile
requires only a new settings row.

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