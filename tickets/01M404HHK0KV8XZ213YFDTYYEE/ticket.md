+++
id = "01M404HHK0KV8XZ213YFDTYYEE"
title = "Design consistency pass: resolve the planner's fifteen contradictions"
type = "docs"
category = "in-progress"
priority = "high"
points = 3
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T05:42:11Z"
updated = "2026-10-03T05:42:12Z"
idempotency_key = "m2-design-consistency-pass-2"
labels = ["milestone:2"]
scope = ["docs/design/**", "notes/review/design-consistency-2.md"]

[[acceptance]]
text = "Given notes/review/design-consistency-2.md, when each of the fifteen items is looked up, then it names the resolution and the design text that now states it"
bound = false
+++

The milestone-2 planner listed fifteen contradictions or gaps across plugins.md, security.md, packs.md, navigation.md, releases and others (plan-cache location, findings cache in the work tree, two meanings of pack, crate homes, GRL rewrites versus tier-0 rules, ledger migration to the ticket branch, GATE001 reviewer label, base findings for no-new-unknowns, which lock holds process-pack digests, CI rule id, PM rule crate, teaching counters, test ticket type, autolink, kernel replaces in CI). Resolve each in the design text and record the resolutions in one place (notes/review/design-consistency-2.md) with the decision log row D85.
