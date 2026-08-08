---
id: T-1843
title: wire find_policy_weakenings (INV-051) into a frob check gate over design/ policies
state: queued
kind: feature
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-1482 built find_policy_weakenings (src/frob/strata/_policy.py) as a pure TIER-1 diff pass over already-compiled CompiledPolicies, proving INV-051 (refinement monotonicity: a narrower-scope policy may only strengthen, never weaken, a confine_use/at_call_require_arg/mediate rule an containing policy already declares for the same target atom). It has no caller outside its own tests (WIRE001, waived on this ticket naming this follow-up). Wire it into a frob check gate that runs it over the real design/ policies loaded via load_design_ids/compile_policies, so a real weakening in design/frob.strata surfaces as a gate finding, not just an available-but-unused function.