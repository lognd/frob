---
id: T-4112
title: 'H3-2: an unauthenticated route writing to a carries-bearing store needs a
  declared inbound rate, not just retention'
state: queued
kind: security
origin: human
created: '2026-09-06'
priority: critical
blocked_by:
- T-4110
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_inbound_rate.py
- tests/unit/strata/test_inbound_rate.py
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
F-307 H3-2 (verbatim, quoted at the bottom of T-4109's body). A carries-
bearing store fed from an unauthenticated route had a declared retention
bound (a TIME bound: how long collected data is kept) but no declared RATE
bound (how much an anonymous caller can write per unit time) -- unbounded
write amplification is invisible to the gate set today. The parent epic
names this "REL201-style, applied to writes": REL201 already requires an
outbound flow to declare a rate; H3-2 is the same discipline for an INBOUND
flow into a carries-bearing store, gated on the route's auth posture.

Grounding for this leaf (its own module, not modifying the outbound family
in place -- REL200/REL201 live in src/frob/strata/_reliability.py, whose own
module docstring already tells future authors to "add your REL2xx rule
alongside REL200/REL201, one home, no duplication"; this new rule reads
in the OPPOSITE direction of every existing REL2xx, so treat it as its own
new file, cross-referencing _reliability.py's constant-naming convention
rather than editing REL200/REL201's file in place under this scope).

Work:
- a rule (suggest REL210) requiring: any store node carrying a
  behavioral/PII-shaped attribute (however this repo's strata surface
  already tags a carries-bearing store -- reuse that existing tag, do not
  invent a new one) that is written by a flow originating from a route
  declared with no auth requirement must have a declared rate on that
  INBOUND flow
- must not duplicate REL201 or re-fire on an outbound flow

Fixture note: this concerns a route/auth/store shape frob's own tree does
not have (frob has no HTTP routes). Build a small synthetic fixture design
(.strata-shaped nodes/flows under the test directory only) with:
- must-fire: an unauthenticated route -> carries-bearing store flow with a
  retention attribute but no rate attribute
- must-stay-quiet: the same shape but WITH a declared inbound rate
- third: an AUTHENTICATED route -> carries-bearing store flow with no rate
  (must stay quiet -- the rule is scoped to unauthenticated write paths only,
  per the finding's own framing)
FLAG EXPLICITLY in the Done report that the fixture is synthetic, not drawn
from frob's own dogfood surface.

frob:ticket T-4109