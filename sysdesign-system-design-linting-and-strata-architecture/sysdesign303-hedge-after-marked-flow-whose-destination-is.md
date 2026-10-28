+++
id = "01M3AXSDA5EX0R2Q2A1ZYFWQ88"
title = "SYSDESIGN303: `hedge_after`-marked flow whose destination is not idempotent"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3AXSDASH31CMNHAQ9JXR1YQ"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-28T12:57:46Z"
aliases = ["T-6469"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0", "no-story"]
scope = ["src/frob/strata/_hedge.py (new)", "tests/fixtures/sysdesign/sysdesign303/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSDA3YQT0T9J3PNZTK1EQ"
+++

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

no-story: internal engineering task in src/frob; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
