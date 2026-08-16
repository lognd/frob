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
runs_last: false
scope:
- src/frob/tickets/_profile.py
- docs/modules/tickets-verify-sweep.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/tickets/_land.py
  reason: 'Coordinator sequencing: release the land-path lease T-1696 is not yet

    using, so two longer-starved tickets can proceed.


    T-1696''s seam enumeration is complete and its agent correctly stopped

    before collapsing anything -- nothing is committed and no land-path file

    has been edited. The collapse itself is a multi-session job (~8300 lines

    across _land.py/_land_cmd.py, with a "prove behavior matches, not just

    tests pass" bar), so holding these two files meanwhile blocks work that

    has waited longer: T-1638 (undispatched 96h) and T-1748 (72h), both of

    which need src/frob/tickets/_land.py and were blocked by this lease

    today.


    The enumeration is preserved in the ticket''s Done-report material and is

    not lost by releasing the lease; re-acquiring these paths when the

    collapse actually begins is a scope --add away. Keeping _profile.py and

    docs/modules/tickets.md in scope since the ProfileSettings design work

    lives there.

    '
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'Coordinator sequencing: release the land-path lease T-1696 is not yet

    using, so two longer-starved tickets can proceed.


    T-1696''s seam enumeration is complete and its agent correctly stopped

    before collapsing anything -- nothing is committed and no land-path file

    has been edited. The collapse itself is a multi-session job (~8300 lines

    across _land.py/_land_cmd.py, with a "prove behavior matches, not just

    tests pass" bar), so holding these two files meanwhile blocks work that

    has waited longer: T-1638 (undispatched 96h) and T-1748 (72h), both of

    which need src/frob/tickets/_land.py and were blocked by this lease

    today.


    The enumeration is preserved in the ticket''s Done-report material and is

    not lost by releasing the lease; re-acquiring these paths when the

    collapse actually begins is a scope --add away. Keeping _profile.py and

    docs/modules/tickets.md in scope since the ProfileSettings design work

    lives there.

    '
  actor: logan
  at: '2026-08-10'
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

## Failure log
- 2026-08-16 attempt 1: acceptance requires no ProfileName branches outside this module, but live branches exist in _land.py, _land_cmd.py, _evidence.py, _close_cmd.py, _backpressure.py, all outside declared scope; undoable as scoped, needs a replan widening scope first
