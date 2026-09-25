---
id: T-draft-9b10d867
title: 'SYSDESIGN303: `hedge_after`-marked flow whose destination is not idempotent'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
blocked_by:
- T-draft-971da3f3
parent: T-draft-ce656788
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
- src/frob/strata/_hedge.py (new)
- tests/fixtures/sysdesign/sysdesign303/**
scope_breadth_ack: true
scope_breadth_ack_reason: sysdesign epic tree, scope reviewed by coordinator
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN303: hedge_after-marked flow whose destination is not idempotent
kind: feature
tier: leaf
parent: T-SYS-SE
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/strata/_hedge.py (new), docs/modules/gates.md (SYSDESIGN303 row),
       tests/fixtures/sysdesign/sysdesign303/**
blocked_by: [T-SYS-A-FLOW-HEDGE]
tag: Static: design (declared-vs-observed, REL221-shaped sibling)

Finding (STRATA-EXPRESSIVENESS.md, section B, "deadline propagation... request hedging"):
"Request hedging: NOT EXPRESSIBLE, zero token. Proposal (GRAMMAR) for hedging: flow_prop
`hedge after QUANTITY`... Enables RULE: hedge-without-idempotent-dst check (REL221-shaped
sibling). Authority: Google SRE book ch.20 (hedged requests), Envoy hedge policy."

Acceptance criteria: reads the `hedge_after` attr from T-SYS-A-FLOW-HEDGE's new grammar; flags
a flow declaring `hedge_after` whose destination node is neither `idempotent` nor covered by a
declared idempotency key (same idempotency test REL221 already runs, reused not re-implemented).
Positive-control fixture: tests/fixtures/sysdesign/sysdesign303/hedge-non-idempotent-dst/**.
