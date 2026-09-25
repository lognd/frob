---
id: T-6467
title: 'GRAMMAR: flow `hedge after QUANTITY` for request hedging'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-6434
parent: T-6510
tier: ticket
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- strata-core/src/parse/grammar_flow.rs
- docs/strata/surface.md#flow
- src/frob/strata/_models.py
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'DOC006 inline waivers: body names files this ticket will create (T-6448)'
  actor: logan
  at: '2026-09-25'
  old_length: 1249
  new_length: 1338
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
OWNER-OWNED: strata surface change; owner reviews before dispatch


title: GRAMMAR: flow hedge after QUANTITY for request hedging
kind: feature (OWNER-OWNED)
tier: leaf
parent: T-SYS-SA
milestone: 0.539.0
sprint: sysdesign
points: 2
scope: strata-core/src/parse/grammar_flow.rs, docs/strata/surface.md#flow,
       src/frob/strata/_models.py, tests/fixtures/sysdesign/flow-hedge/**
blocked_by: [T-STORE-301-ATTR]

Finding (STRATA-EXPRESSIVENESS.md, section B "COMMUNICATION"):

"Request hedging: NOT EXPRESSIBLE, zero token. Proposal (GRAMMAR) for hedging: flow_prop
`hedge after QUANTITY`, lives grammar_flow.rs, desugars to attr `hedge_after=<q>`. Enables
RULE: hedge-without-idempotent-dst check (REL221-shaped sibling). Authority: Google SRE book
ch.20 (hedged requests), Envoy hedge policy."

Acceptance criteria: flow_prop gains `hedge after QUANTITY`, desugars to attr `hedge_after=`,
registered in T-STORE-301-ATTR's table. Downstream RULE leaf (SYSDESIGN303, Story E) is
blocked_by this ticket. Positive-control fixture: tests/fixtures/sysdesign/flow-hedge/
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->hedge-non-idempotent-dst/design.strata.
