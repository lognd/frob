---
id: T-2693
title: TICK006 phantom-refile of T-draft-be1e79b5 (cited by T-2685) collides with
  T-2689's identical title/scope
state: queued
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-2685
- tickets/T-2689
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
T-2685's Done report carries a phantom TICK006 citation of
`T-draft-be1e79b5`, which the land-time Tier-A auto-fix
(`fix_tick006_phantom_refile`) tries to resolve by refiling that draft
as a real ticket titled "Recovered from T-2685's phantom TICK006
citation of T-draft-be1e79b5". That refile fails every time with
`DuplicateTicket: an existing ticket already has this exact title and
this exact scope` -- T-2689 already carries that exact title and scope.

Effect: the failed refile leaves a live, non-empty-rule-id TICK006
finding on `tickets.md` that persists across every `frob check` and
`frob ticket land` run touching the ledger, surfacing as a genuine
`ClaimDivergence` for whatever UNRELATED ticket happens to land next
(observed directly: it fired against T-2141's land, 2026-08-19/20,
naming `[('TICK006', 'tickets.md')]` as a new in-scope finding -- T-2141
never touched T-2685/T-2689/T-draft-be1e79b5 at all).

Fix: either drop/reuse T-2689 per the refusal's own suggestion, or
repair T-2685's citation directly so `fix_tick006_phantom_refile` has
nothing left to refile. Whichever path, the TICK006 finding needs to
actually clear -- it is currently a standing tax on every OTHER ticket's
land that happens to touch `tickets.md` (which is implicitly in scope
for everything).
