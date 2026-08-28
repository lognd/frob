---
id: T-2693
title: TICK006 phantom-refile of T-draft-be1e79b5 (cited by T-2685) collides with
  T-2689's identical title/scope
state: done
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
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): premise stale: the standing TICK006 finding
    for T-2685/T-2689/T-draft-be1e79b5 this ticket was filed to fix no longer exists
    on main, already resolved by the T-2690->T-2699->T-2701->T-2702 chain (T-2702
    landed the real fix, e983c75cdbbc74601a056fcb5d123b1a68412907, with a designated
    repro test for exactly this two-lands-cite-same-draft shape); T-2689 is itself
    dropped. Measured directly via frob check --only tickets: zero TICK006 findings
    name T-2685/T-2689/T-draft-be1e79b5 today. No code change needed.'
  actor: logan
  at: '2026-08-27'
  old_length: 1290
  new_length: 1833
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_tick006_two_lands_citing_same_draft_produce_at_most_one_ticket
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0df755195f5f5e30ccf65dc36364f27c8d663147
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

frob:no-behavior-change reason="premise stale: the standing TICK006 finding for T-2685/T-2689/T-draft-be1e79b5 this ticket was filed to fix no longer exists on main, already resolved by the T-2690->T-2699->T-2701->T-2702 chain (T-2702 landed the real fix, e983c75cdbbc74601a056fcb5d123b1a68412907, with a designated repro test for exactly this two-lands-cite-same-draft shape); T-2689 is itself dropped. Measured directly via frob check --only tickets: zero TICK006 findings name T-2685/T-2689/T-draft-be1e79b5 today. No code change needed."