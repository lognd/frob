+++
id = "01M3AXSDA3YQT0T9J3PNZTK1EQ"
title = "GRAMMAR: flow `hedge after QUANTITY` for request hedging"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSDBEQGV8V5VHYGXBEQTV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-09T20:42:22Z"
aliases = ["T-6467"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["strata-core/src/parse/grammar_flow.rs", "src/frob/strata/_models.py", "docs/design/grmb-spec.md"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD926S7M96AQB9BTK4E2"
+++

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
