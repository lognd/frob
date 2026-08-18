---
id: T-2362
title: 'Profile-collapse: add a structural gate against ProfileName branches outside
  _profile.py'
state: queued
kind: feature
origin: human
created: '2026-08-17'
priority: medium
blocked_by:
- T-2361
parent: T-1696
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-1696 (queue-depth-dial collapse epic), closing leaf --
BLOCKED on the migration child (nothing to statically enforce against
until the seams it removes are actually gone).

The epic's own body: "A grep for the profile enum outside the settings
module should return nothing, and that is worth a gate rule of its own
if it is cheap to add." Add that gate rule.

A static check (frob.gates, or a `frob check --only` stage) that fails
when `ProfileName` (or `effective_profile`/`configured_profile`) is
referenced outside src/frob/tickets/_profile.py and the settings-resolver
module built by the first child -- using the symbol/reference graph
(frob.graph), the same mechanism `frob explore xref` already uses for
this exact query manually, never a lexical grep/regex over source text
(standing repo constraint: SYMBOLIC, NEVER LEXICAL).

This closes the loop the epic exists for: without this gate, a future
change can silently reintroduce an if-rapid-shaped seam and nothing
will catch it until someone happens to re-run the same manual xref query
a coordinator ran by hand today.

Acceptance:
- A gate rule (new rule id, or an extension of an existing structural
  gate if one already fits -- check before adding a new id, per the
  repo's own no-duplication rule) fires on a DELIBERATELY reintroduced
  ProfileName branch outside the allowed module(s) -- a positive control,
  not just "the gate exists".
- The gate passes clean on the post-migration tree (0 findings).
- Documented in docs/modules/gates.md alongside the other structural
  gates.
